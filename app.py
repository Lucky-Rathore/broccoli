from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import boto3
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import json
from pydantic import BaseModel
import os
from botocore.exceptions import ClientError, NoCredentialsError

app = FastAPI(title="AWS Cost Analysis API", version="1.0.0")

# Pydantic models for request/response
class CostRequest(BaseModel):
    start_date: str
    end_date: str
    granularity: str = "DAILY"  # DAILY, MONTHLY, HOURLY
    group_by: Optional[str] = None  # SERVICE, REGION, USAGE_TYPE, etc.

class CostResponse(BaseModel):
    total_cost: float
    currency: str
    data: List[Dict]
    chart_data: Dict

# Initialize boto3 client
def get_cost_explorer_client():
    try:
        return boto3.client('ce', region_name='ap-south-1')  # Cost Explorer is only available in ap-south-1
    except NoCredentialsError:
        raise HTTPException(
            status_code=500, 
            detail="AWS credentials not configured. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables."
        )

@app.get("/")
async def root():
    return {"message": "AWS Cost Analysis API", "docs": "/docs"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/costs/analyze", response_model=CostResponse)
async def analyze_costs(request: CostRequest):
    """
    Analyze AWS costs for a given time period
    """
    try:
        ce_client = get_cost_explorer_client()
        
        # Validate dates
        start_date = datetime.fromisoformat(request.start_date.replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(request.end_date.replace('Z', '+00:00'))
        
        if start_date >= end_date:
            raise HTTPException(status_code=400, detail="Start date must be before end date")
        
        # Build the query
        query = {
            'TimePeriod': {
                'Start': start_date.strftime('%Y-%m-%d'),
                'End': end_date.strftime('%Y-%m-%d')
            },
            'Granularity': request.granularity,
            'Metrics': ['BlendedCost', 'UnblendedCost', 'UsageQuantity']
        }
        
        # Add group by if specified
        if request.group_by:
            query['GroupBy'] = [{'Type': 'DIMENSION', 'Key': request.group_by}]
        
        # Get cost data
        response = ce_client.get_cost_and_usage(**query)
        
        # Process the response
        total_cost = 0.0
        currency = "USD"
        data = []
        chart_data = {"labels": [], "datasets": []}
        
        for result in response['ResultsByTime']:
            period_start = result['TimePeriod']['Start']
            period_end = result['TimePeriod']['End']
            
            if result['Groups']:
                # Grouped data
                for group in result['Groups']:
                    group_key = group['Keys'][0] if group['Keys'] else 'Unknown'
                    cost = float(group['Metrics']['BlendedCost']['Amount'])
                    total_cost += cost
                    currency = group['Metrics']['BlendedCost']['Unit']
                    
                    data.append({
                        'period_start': period_start,
                        'period_end': period_end,
                        'group': group_key,
                        'cost': cost,
                        'currency': currency
                    })
            else:
                # Non-grouped data
                cost = float(result['Total']['BlendedCost']['Amount'])
                total_cost += cost
                currency = result['Total']['BlendedCost']['Unit']
                
                data.append({
                    'period_start': period_start,
                    'period_end': period_end,
                    'cost': cost,
                    'currency': currency
                })
                
                chart_data['labels'].append(period_start)
        
        # Prepare chart data
        if not request.group_by:
            # Simple line chart data
            chart_data['datasets'] = [{
                'label': 'Cost',
                'data': [item['cost'] for item in data],
                'borderColor': 'rgb(75, 192, 192)',
                'backgroundColor': 'rgba(75, 192, 192, 0.2)'
            }]
        else:
            # Grouped chart data
            groups = {}
            for item in data:
                group_name = item.get('group', 'Unknown')
                if group_name not in groups:
                    groups[group_name] = []
                groups[group_name].append(item['cost'])
            
            chart_data['datasets'] = []
            colors = ['rgb(255, 99, 132)', 'rgb(54, 162, 235)', 'rgb(255, 205, 86)', 
                     'rgb(75, 192, 192)', 'rgb(153, 102, 255)', 'rgb(255, 159, 64)']
            
            for i, (group_name, costs) in enumerate(groups.items()):
                chart_data['datasets'].append({
                    'label': group_name,
                    'data': costs,
                    'borderColor': colors[i % len(colors)],
                    'backgroundColor': colors[i % len(colors)].replace('rgb', 'rgba').replace(')', ', 0.2)')
                })
        
        return CostResponse(
            total_cost=round(total_cost, 2),
            currency=currency,
            data=data,
            chart_data=chart_data
        )
        
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"AWS API Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/costs/services")
async def get_top_services(
    days: int = Query(30, description="Number of days to look back"),
    limit: int = Query(10, description="Number of top services to return")
):
    """
    Get top services by cost
    """
    try:
        ce_client = get_cost_explorer_client()
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date.strftime('%Y-%m-%d'),
                'End': end_date.strftime('%Y-%m-%d')
            },
            Granularity='MONTHLY',
            Metrics=['BlendedCost'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
        )
        
        services = {}
        for result in response['ResultsByTime']:
            for group in result['Groups']:
                service = group['Keys'][0] if group['Keys'] else 'Unknown'
                cost = float(group['Metrics']['BlendedCost']['Amount'])
                
                if service in services:
                    services[service] += cost
                else:
                    services[service] = cost
        
        # Sort by cost and get top services
        top_services = sorted(services.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        return {
            'top_services': [{'service': service, 'cost': round(cost, 2)} for service, cost in top_services],
            'total_services': len(services),
            'period_days': days
        }
        
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"AWS API Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """
    HTML dashboard with interactive charts
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AWS Cost Analysis Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .card { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .controls { display: flex; gap: 15px; align-items: center; margin-bottom: 20px; }
            .controls input, .controls select, .controls button { padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; }
            .controls button { background: #007bff; color: white; border: none; cursor: pointer; }
            .controls button:hover { background: #0056b3; }
            .chart-container { position: relative; height: 400px; margin: 20px 0; }
            .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
            .metric { text-align: center; padding: 15px; background: #e3f2fd; border-radius: 8px; }
            .metric h3 { margin: 0 0 10px 0; color: #1976d2; }
            .metric p { margin: 0; font-size: 24px; font-weight: bold; color: #333; }
            .loading { text-align: center; color: #666; }
            .error { color: #d32f2f; background: #ffebee; padding: 10px; border-radius: 4px; margin: 10px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>AWS Cost Analysis Dashboard</h1>
            
            <div class="card">
                <h2>Cost Analysis</h2>
                <div class="controls">
                    <label>Start Date: < type="date" id="startDate"></label>
                    <label>End Date: <input type="date" id="endDate"></label>
                    <label>Granularity: 
                        <select id="granularity">
                            <option value="DAILY">Daily</option>
                            <option value="MONTHLY">Monthly</option>
                        </select>
                    </label>
                    <label>Group By: 
                        <select id="groupBy">
                            <option value="">None</option>
                            <option value="SERVICE">Service</option>
                            <option value="REGION">Region</option>
                            <option value="USAGE_TYPE">Usage Type</option>
                        </select>
                    </label>
                    <button onclick="analyzeCosts()">Analyze</button>
                </div>
                
                <div id="loading" class="loading" style="display: none;">Loading...</div>
                <div id="error" class="error" style="display: none;"></div>
                
                <div class="metrics">
                    <div class="metric">
                        <h3>Total Cost</h3>
                        <p id="totalCost">$0.00</p>
                    </div>
                    <div class="metric">
                        <h3>Average Daily Cost</h3>
                        <p id="avgCost">$0.00</p>
                    </div>
                    <div class="metric">
                        <h3>Currency</h3>
                        <p id="currency">USD</p>
                    </div>
                </div>
                
                <div class="chart-container">
                    <canvas id="costChart"></canvas>
                </div>
            </div>
            
            <div class="card">
                <h2>Top Services</h2>
                <div class="controls">
                    <label>Days: <input type="number" id="serviceDays" value="30" min="1" max="365"></label>
                    <button onclick="getTopServices()">Refresh</button>
                </div>
                <div class="chart-container">
                    <canvas id="servicesChart"></canvas>
                </div>
            </div>
        </div>

        <script>
            let costChart = null;
            let servicesChart = null;
            
            // Initialize default dates
            const today = new Date();
            const thirtyDaysAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
            
            document.getElementById('startDate').value = thirtyDaysAgo.toISOString().split('T')[0];
            document.getElementById('endDate').value = today.toISOString().split('T')[0];
            
            async function analyzeCosts() {
                const startDate = document.getElementById('startDate').value;
                const endDate = document.getElementById('endDate').value;
                const granularity = document.getElementById('granularity').value;
                const groupBy = document.getElementById('groupBy').value;
                
                if (!startDate || !endDate) {
                    showError('Please select both start and end dates');
                    return;
                }
                
                showLoading(true);
                hideError();
                
                try {
                    const response = await fetch('/costs/analyze', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            start_date: startDate,
                            end_date: endDate,
                            granularity: granularity,
                            group_by: groupBy || null
                        })
                    });
                    
                    if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.detail || 'Failed to analyze costs');
                    }
                    
                    const data = await response.json();
                    updateMetrics(data);
                    updateCostChart(data.chart_data);
                    
                } catch (error) {
                    showError(error.message);
                } finally {
                    showLoading(false);
                }
            }
            
            async function getTopServices() {
                const days = document.getElementById('serviceDays').value;
                
                try {
                    const response = await fetch(`/costs/services?days=${days}&limit=10`);
                    
                    if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.detail || 'Failed to get top services');
                    }
                    
                    const data = await response.json();
                    updateServicesChart(data.top_services);
                    
                } catch (error) {
                    showError(error.message);
                }
            }
            
            function updateMetrics(data) {
                document.getElementById('totalCost').textContent = `$${data.total_cost.toFixed(2)}`;
                document.getElementById('currency').textContent = data.currency;
                
                const days = data.data.length || 1;
                const avgCost = data.total_cost / days;
                document.getElementById('avgCost').textContent = `$${avgCost.toFixed(2)}`;
            }
            
            function updateCostChart(chartData) {
                const ctx = document.getElementById('costChart').getContext('2d');
                
                if (costChart) {
                    costChart.destroy();
                }
                
                costChart = new Chart(ctx, {
                    type: 'line',
                    data: chartData,
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            title: { display: true, text: 'Cost Over Time' }
                        },
                        scales: {
                            y: { beginAtZero: true }
                        }
                    }
                });
            }
            
            function updateServicesChart(services) {
                const ctx = document.getElementById('servicesChart').getContext('2d');
                
                if (servicesChart) {
                    servicesChart.destroy();
                }
                
                servicesChart = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: services.map(s => s.service),
                        datasets: [{
                            label: 'Cost ($)',
                            data: services.map(s => s.cost),
                            backgroundColor: 'rgba(54, 162, 235, 0.6)',
                            borderColor: 'rgba(54, 162, 235, 1)',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            title: { display: true, text: 'Top Services by Cost' }
                        },
                        scales: {
                            y: { beginAtZero: true }
                        }
                    }
                });
            }
            
            function showLoading(show) {
                document.getElementById('loading').style.display = show ? 'block' : 'none';
            }
            
            function showError(message) {
                const errorDiv = document.getElementById('error');
                errorDiv.textContent = message;
                errorDiv.style.display = 'block';
            }
            
            function hideError() {
                document.getElementById('error').style.display = 'none';
            }
            
            // Load initial data
            window.onload = function() {
                analyzeCosts();
                getTopServices();
            };
        </script>
    </body>
    </html>
    """
    return html_content

@app.get("/costs/forecast")
async def get_cost_forecast(days: int = Query(30, description="Number of days to forecast")):
    """
    Get cost forecast using AWS Cost Explorer
    """
    try:
        ce_client = get_cost_explorer_client()
        
        start_date = datetime.now()
        end_date = start_date + timedelta(days=days)
        
        response = ce_client.get_cost_forecast(
            TimePeriod={
                'Start': start_date.strftime('%Y-%m-%d'),
                'End': end_date.strftime('%Y-%m-%d')
            },
            Metric='BLENDED_COST',
            Granularity='DAILY'
        )
        
        forecast_data = []
        for result in response['ForecastResultsByTime']:
            forecast_data.append({
                'date': result['TimePeriod']['Start'],
                'mean_value': float(result['MeanValue']),
                'prediction_interval_lower': float(result['PredictionIntervalLowerBound']),
                'prediction_interval_upper': float(result['PredictionIntervalUpperBound'])
            })
        
        return {
            'forecast_data': forecast_data,
            'total_forecast': sum(item['mean_value'] for item in forecast_data),
            'currency': 'USD',
            'forecast_days': days
        }
        
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"AWS API Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
