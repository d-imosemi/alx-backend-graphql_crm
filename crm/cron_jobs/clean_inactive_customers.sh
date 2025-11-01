#!/bin/bash
# this script should delete customers with no orders since a year ago

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="$(basename "$(dirname "$(dirname "$SCRIPT_DIR")")")"

TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S" --date="1 year ago")

python3 manage.py shell << EOF
from crm.models import Customer
from django.utils import timezone

threshold_date = timezone.now() - timezone.timedelta(days=365)
inactive_customers = Customer.objects.filter(last_order_date__lt=threshold_date)
# count the number of inactive customers
print(f"Found {inactive_customers.count()} inactive customers to delete.")

inactive_customers.delete()
EOF
print "Inactive customers cleaned up successfully."

# log results to a file
echo "$(date +"%Y-%m-%d %H:%M:%S") - Cleaned up inactive customers." >> /tmp/customer_cleanup_log.txt