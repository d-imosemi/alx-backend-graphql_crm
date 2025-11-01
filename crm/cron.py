from datetime import datetime
import datetime
from unittest import result
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from .schema import UpdateLowStockProducts


# Logs a message CRM is alive to /tmp/crm_heartbeat_log.txt
def log_crm_heartbeat():
    try:
        import requests
        response = requests.post(
            "http://localhost:8000/graphql",
            json={"query": "{ hello }"}
        )
        response_data = response.json()
        if 'data' in response_data and 'hello' in response_data['data']:
            with open("/tmp/crm_heartbeat_log.txt", "a") as log_file:
                timestamp = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
                log_file.write(f"{timestamp} CRM is alive\n")
            print("CRM heartbeat logged successfully.")
        else:
            print("GraphQL endpoint did not return expected data.")
    except Exception as e:
        print(f"Error occurred while logging CRM heartbeat: {e}")

def update_low_stock():
    """Function to update low stock products using GraphQL mutation"""
    GRAPHQL_URL = "http://localhost:8000/graphql"

    # Initialize GraphQL client
    transport = RequestsHTTPTransport(url=GRAPHQL_URL, verify=True, retries=3)
    client = Client(transport=transport, fetch_schema_from_transport=True)

    # Define mutation
    mutation = gql("""
    mutation {
        updateLowStockProducts {
            success
            message
        }
    }
    """)

    try:
        # Logs updated product names and new stock levels
        with open("/tmp/low_stock_updates_log.txt", "a") as log_file:
            for product in result.get('updatedProducts', []):
                log_file.write(f"{datetime.now()} - Product '{product['name']}' updated to {product['stock']} in stock\n")
    except Exception as e:
        print(f"Error occurred while logging low stock updates: {e}")

if __name__ == "__main__":
    log_crm_heartbeat()
    update_low_stock()