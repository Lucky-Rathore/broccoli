# AWS Cost Analysis FastAPI Application

A comprehensive FastAPI application for analyzing AWS costs with interactive dashboards and REST API endpoints. Built with boto3 for AWS integration and Chart.js for data visualization.

## 🚀 Features

- **Interactive Mock Dashboard**: Web-based interface with real-time charts
- **Cost Analysis**: Analyze costs by time period, service, region, and usage type
- **Forecasting**: AWS Cost Explorer integration for cost predictions
- **Multiple Granularities**: Daily, Monthly, and Hourly cost breakdowns
- **Top Services**: Identify highest-cost AWS services
- **REST API**: Full API with automatic documentation
- **Error Handling**: Comprehensive error handling and validation

## 📋 Prerequisites

- Python 3.8+
- AWS Account with Cost Explorer enabled
- AWS CLI configured or AWS credentials set up
- IAM permissions for Cost Explorer API

## 🛠️ Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd aws-cost-analysis
```

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Set up AWS credentials** (choose one method):

   **Option A: Environment Variables**
   ```bash
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_DEFAULT_REGION=us-east-1
   ```

   **Option B: AWS CLI**
   ```bash
   aws configure
   ```

   **Option C: IAM Role** (for EC2 instances)
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "ce:GetCostAndUsage",
           "ce:GetCostForecast",
           "ce:GetDimensionValues",
           "ce:GetReservationCoverage",
           "ce:GetReservationPurchaseRecommendation",
           "ce:GetReservationUtilization",
           "ce:GetRightsizingRecommendation",
           "ce:GetUsageForecast"
         ],
         "Resource": "*"
       }
     ]
   }
   ```

## 🚀 Quick Start

1. **Run the application**:
```bash
python main.py
```

2. **Access the dashboard**:
   - Open your browser and go to: `http://localhost:8000/dashboard`

3. **View API documentation**:
   - Swagger UI: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

## 📊 Dashboard Features

### Cost Analysis Section
- **Date Range Selection**: Pick start and end dates
- **Granularity Options**: Daily, Monthly, Hourly
- **Grouping Options**: Service, Region, Usage Type
- **Interactive Charts**: Line charts for cost trends

### Metrics Cards
- **Total Cost**: Sum of all costs in the selected period
- **Average Daily Cost**: Daily average cost calculation
- **Currency**: Display currency (USD)

### Top Services
- **Service Breakdown**: Bar chart of highest-cost services
- **Configurable Period**: Adjust days to analyze
- **Cost Ranking**: Services sorted by cost

## 🔌 API Endpoints

### Core Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root endpoint |
| GET | `/health` | Health check |
| GET | `/dashboard` | Interactive dashboard |
| GET | `/docs` | API documentation |

### Cost Analysis Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/costs/analyze` | Analyze costs for time period |
| GET | `/costs/services` | Get top services by cost |
| GET | `/costs/forecast` | Get cost forecast |

## 📝 API Usage Examples

### 1. Basic Cost Analysis
```bash
curl -X POST "http://localhost:8000/costs/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-06-15",
    "end_date": "2024-07-15",
    "granularity": "DAILY"
  }'
```

### 2. Cost Analysis by Service
```bash
curl -X POST "http://localhost:8000/costs/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-06-15",
    "end_date": "2024-07-15",
    "granularity": "DAILY",
    "group_by": "SERVICE"
  }'
```

### 3. Top Services
```bash
curl "http://localhost:8000/costs/services?days=30&limit=10"
```

### 4. Cost Forecast
```bash
curl "http://localhost:8000/costs/forecast?days=30"
```

## 📂 Project Structure

```
aws-cost-analysis/
├── main.py              # FastAPI application
├── requirements.txt     # Python dependencies
├── README.md           # Project documentation
├── curl_samples.sh     # Sample curl commands
└── static/             # Static files (if needed)
```

## 🔧 Configuration

### Environment Variables
```bash
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1
```

### Cost Explorer Settings
- **Region**: Cost Explorer API is only available in `us-east-1`
- **Billing Data**: Ensure billing data is available in your AWS account
- **Permissions**: Requires appropriate IAM permissions

## 📊 Sample Response Format

### Cost Analysis Response
```json
{
  "total_cost": 123.45,
  "currency": "USD",
  "data": [
    {
      "period_start": "2024-07-01",
      "period_end": "2024-07-02",
      "cost": 12.34,
      "currency": "USD"
    }
  ],
  "chart_data": {
    "labels": ["2024-07-01", "2024-07-02"],
    "datasets": [
      {
        "label": "Cost",
        "data": [12.34, 15.67],
        "borderColor": "rgb(75, 192, 192)"
      }
    ]
  }
}
```

### Top Services Response
```json
{
  "top_services": [
    {
      "service": "Amazon Elastic Compute Cloud - Compute",
      "cost": 45.67
    },
    {
      "service": "Amazon Simple Storage Service",
      "cost": 23.45
    }
  ],
  "total_services": 15,
  "period_days": 30
}
```

## 🐳 Docker Deployment

Create a `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t aws-cost-analyzer .
docker run -p 8000:8000 -e AWS_ACCESS_KEY_ID=your_key -e AWS_SECRET_ACCESS_KEY=your_secret aws-cost-analyzer
```

## 🔍 Troubleshooting

### Common Issues

1. **AWS Credentials Error**
   - Ensure AWS credentials are properly configured
   - Check IAM permissions for Cost Explorer

2. **No Data Available**
   - Verify billing data exists in your AWS account
   - Check date ranges are valid

3. **Region Issues**
   - Cost Explorer API only works in `us-east-1`
   - Ensure your client is configured for the correct region

4. **CORS Issues**
   - Add proper CORS headers for browser access
   - Use the dashboard at `/dashboard` instead of direct API calls

### Debug Mode
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level debug
```

## 📈 Performance Considerations

- **Caching**: Consider implementing Redis caching for frequently accessed data
- **Rate Limiting**: AWS Cost Explorer has API rate limits
- **Data Aggregation**: Large date ranges may take longer to process
- **Pagination**: Implement pagination for large datasets

## 🔒 Security Best Practices

- **Never commit AWS credentials** to version control
- **Use IAM roles** when possible (recommended for production)
- **Implement authentication** for production deployments
- **Use HTTPS** in production environments
- **Set up proper CORS** policies
- **Monitor API usage** and implement rate limiting

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the troubleshooting section above
- Review AWS Cost Explorer documentation

## 🎯 Future Enhancements

- [ ] Add authentication and authorization
- [ ] Implement data caching with Redis
- [ ] Add more chart types and visualizations
- [ ] Export data to CSV/PDF
- [ ] Add cost optimization recommendations
- [ ] Implement real-time cost alerts
- [ ] Add multi-account support
- [ ] Create mobile-responsive design improvements

## 📚 Additional Resources

- [AWS Cost Explorer API Documentation](https://docs.aws.amazon.com/cost-management/latest/APIReference/API_Operations_AWS_Cost_Explorer_Service.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [Chart.js Documentation](https://www.chartjs.org/docs/)

---

**Made with ❤️ for AWS cost optimization**