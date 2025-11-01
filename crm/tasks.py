import requests
from celery import shared_task
from datetime import datetime

GRAPHQL_URL = "http://localhost:8000/graphql"

# Graphql query to fetch crm statistics
CRM_STATS_QUERY = """
query { crmStatistics {
    totalCustomers: customers {
        count
    }
    totalOrders: orders {
        count
    }
    totalRevenue: orders {
        totalAmount
    }
  }
}
"""

@shared_task
def generate_crm_report():
    """Generates a CRM report by fetching statistics via GraphQL and saving to a file."""
    try:
        response = requests.post(
            GRAPHQL_URL,
            json={"query": CRM_STATS_QUERY}
        )
        response_data = response.json()
        stats = response_data['data']['crmStatistics']

        # calculate totals
        total_customers = stats['totalCustomers']['count']
        total_orders = stats['totalOrders']['count']
        total_revenue = stats['totalRevenue']['totalAmount']

        report_content = (
            f"YYYY-MM-DD HH:MM:SS - Report: X customers, Y orders, Z revenue.\n"
            .replace("YYYY-MM-DD HH:MM:SS", requests.utils.formatdate())
            .replace("X", str(total_customers))
            .replace("Y", str(total_orders))
            .replace("Z", str(total_revenue))
        )

        # Save report to a file
        with open("/tmp/crm_report_log.txt", "a") as report_file:
            report_file.write(report_content)

        print("CRM report generated successfully.")
    except Exception as e:
        print(f"Error occurred while generating CRM report: {e}")