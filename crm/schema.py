import graphene
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from .models import Customer, Product, Order
from crm.models import Product
import re
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.db import transaction
from django.db.models import Q
from .filters import CustomerFilter, ProductFilter, OrderFilter

# =============== Object classes =================
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        interfaces = (graphene.relay.Node,)
        filterset_class = CustomerFilter
        fields = ("id", "name", "email", "phone", "created_at", "updated_at")


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        interfaces = (graphene.relay.Node,)
        filterset_class = ProductFilter
        fields = ("id", "name", "price", "stock", "created_at", "updated_at")


class OrderType(DjangoObjectType):
    total_amount = graphene.Decimal()
    customer_name = graphene.String()
    customer_email = graphene.String()
    products = graphene.List(ProductType)

    class Meta:
        model = Order
        interfaces = (graphene.relay.Node,)
        filterset_class = OrderFilter
        fields = ("id", "customer", "order_date", "status", "total_amount", "created_at")

    def resolve_items(self, info):
        return self.items.all()

    def resolve_total_amount(self, info):
        return self.total_amount

    def resolve_customer_name(self, info):
        return self.customer.name if self.customer else None

    def resolve_customer_email(self, info):
        return self.customer.email if self.customer else None

    def resolve_products(self, info):
        return [item.product for item in self.items.all()]


class ErrorType(graphene.ObjectType):
    field = graphene.String()
    message = graphene.String()
    index = graphene.Int()

class BulkCustomerResultType(graphene.ObjectType):
    success = graphene.Boolean()
    customers = graphene.List(CustomerType)
    errors = graphene.List(ErrorType)
    created_count = graphene.Int()
    failed_count = graphene.Int()


# =================== Input types for filtering =============
class CustomerFilterInput(graphene.InputObjectType):
    name = graphene.String()
    email = graphene.String()
    created_at_gte = graphene.Date()
    created_at_lte = graphene.Date()
    phone_pattern = graphene.String()

class ProductFilterInput(graphene.InputObjectType):
    name = graphene.String()
    price_gte = Decimal()
    price_lte = Decimal()
    stock_gte = graphene.Int()
    stock_lte = graphene.Int()
    low_stock = graphene.Boolean()

class OrderFilterInput(graphene.InputObjectType):
    total_amount_gte = Decimal()
    total_amount_lte = Decimal()
    order_date_gte = graphene.Date()
    order_date_lte = graphene.Date()
    customer_name = graphene.String()
    product_name = graphene.String()
    product_id = graphene.ID()

class OrderByInput(graphene.InputObjectType):
    field = graphene.String(required=True)
    direction = graphene.String(default_value="asc")

# =================== Input classes ==================
class CreateCustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String(required=False)

class CreateProductInput(graphene.InputObjectType):
    name= graphene.String(required=True)
    price = graphene.Decimal(required=True)
    stock = graphene.Int(required=False, default_value=0)

class CreateOrderInput(graphene.InputObjectType):
    customer_id = graphene.ID(required=True, description="ID of an existing customer")
    product_ids = graphene.List(graphene.ID, required=True, description="List of existing product IDs")
    order_date = graphene.DateTime(required=False, description="Order date (defaults to now)")

# =================== Validations =====================
class ValidationMethod:
    @staticmethod
    def validate_email(email):
        # To validate email format
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise ValidationError("Please enter a valid email address.")
        
        # Check for unique email
        if Customer.objects.filter(email=email).exists():
            raise ValidationError("A customer with this email already exists.")
        
    @staticmethod
    def validate_phone(phone):
        # Validate phone format if provided
        if phone:
            # Validate phone format: +1234567890 or 123-456-7890
            phone_pattern = r'^(\+\d{10,15}|\d{3}-\d{3}-\d{4})$'
            if not re.match(phone_pattern, phone):
                raise ValidationError(
                    "Phone number must be in format: +1234567890 or 123-456-7890"
                )
    @staticmethod
    def validate_price(price):
        # Validate price is positive
        if price <= Decimal('0'):
            raise ValidationError("Price must be a positive number.")
        
    @staticmethod
    def validate_stock(stock):
        # Validate stock is not negative
        if stock < 0:
            raise ValidationError("Stock cannot be negative")


# =================== Mutation classes ================
class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CreateCustomerInput(required=True)
    
    customer = graphene.Field(CustomerType)
    message = graphene.String()
    success = graphene.Boolean()
    
    def mutate(self, info, input):
        try:
            # Validate Inputs
            ValidationMethod.validate_email(input.email)
            ValidationMethod.validate_phone(input.phone)

            # Create and save customer
            customer = Customer(
                name = input.name,
                email = input.email,
                phone = input.phone
            )
            customer.full_clean()
            customer.save()

            return CreateCustomer(
                customer=customer,
                message="Customer created successfully!",
                success=True
            )
        except ValidationError as e:
            # Handle validation errors
            error_message = str(e)
            if 'email' in str(e).lower():
                error_message = "A customer with this email already exists."
            elif 'phone' in str(e).lower():
                error_message = "Invalid phone format"
            
            return CreateCustomer(
                customer=None,
                message=error_message,
                success=False
            )
        except Exception as e:
            # Handle any other exceptions
            return CreateCustomer(
                customer=None,
                message=f"An error occurred: {str(e)}",
                success=False
            )

class BulkCreateCustomers(graphene.Mutation):
    customers = graphene.List(CustomerType)
    errors = graphene.List(ErrorType)
    class Arguments:
        input = graphene.List(CreateCustomerInput, required=True)

    result = graphene.Field(BulkCustomerResultType)

    def mutate(self, info, input):
        created_customers = []
        errors = []
        
        with transaction.atomic():
            for index, input_data in enumerate(input):
                try:
                    # Validate individual customer
                    ValidationMethod.validate_email(input_data.email)
                    ValidationMethod.validate_phone(input_data.phone)

                    customer = Customer(
                        name=input_data.name,
                        email=input_data.email,
                        phone=input_data.phone
                    )
                    customer.full_clean()
                    customer.save()
                    created_customers.append(customer)

                except Exception as e:
                    error_message = str(e)
                    if 'email' in error_message.lower() and 'already exists' in error_message.lower():
                        error_message = f"Email '{input_data.email}' already exists"
                    elif 'phone' in error_message.lower():
                        error_message = "Invalid phone format"
                    
                    errors.append(ErrorType(
                        field="customer_data",
                        message=error_message,
                        index=index
                    ))

        return BulkCreateCustomers(
            customers=created_customers,
            errors=errors
        )


class CreateProduct(graphene.Mutation):
    class Arguments:
        input = CreateProductInput(required=True)

    product = graphene.Field(ProductType)
    message = graphene.String()
    success = graphene.Boolean()

    def mutate(self, info, input):
        try:
            # Validate inputs
            ValidationMethod.validate_price(input.price)
            ValidationMethod.validate_stock(input.stock)

            product = Product(
                name=input.name,
                price=input.price,
                stock=input.stock or 0
            )
            product.full_clean()
            product.save()

            return CreateProduct(
                product=product,
                message="Product created successfully!",
                success=True
            )

        except ValidationError as e:
            error_message = str(e)
            if 'price' in str(e).lower():
                error_message = "Price must be a positive number"
            elif 'stock' in str(e).lower():
                error_message = "Stock cannot be negative"
            
            return CreateProduct(
                product=None,
                message=error_message,
                success=False
            )
        except Exception as e:
            return CreateProduct(
                product=None,
                message=f"An error occurred: {str(e)}",
                success=False
            )


class CreateOrder(graphene.Mutation):
    class Arguments:
        input = CreateOrderInput(required=True)

    order = graphene.Field(OrderType)
    message = graphene.String()
    success = graphene.Boolean()

    def mutate(self, info, input):
        try:
            # Validate customer exists
            try:
                customer = Customer.objects.get(id=input.customer_id)
            except Customer.DoesNotExist:
                return CreateOrder(
                    order=None,
                    message="Customer not found",
                    success=False
                )

            # Validate products exist and get them
            if not input.product_ids:
                return CreateOrder(
                    order=None,
                    message="At least one product is required",
                    success=False
                )

            products = []
            invalid_product_ids = []
            
            for product_id in input.product_ids:
                try:
                    product = Product.objects.get(id=product_id)
                    products.append(product)
                except Product.DoesNotExist:
                    invalid_product_ids.append(str(product_id))

            if invalid_product_ids:
                return CreateOrder(
                    order=None,
                    message=f"Invalid product IDs: {', '.join(invalid_product_ids)}",
                    success=False
                )

            # Calculate total amount
            total_amount = sum(product.price for product in products)

            # Create order and order items in transaction
            with transaction.atomic():
                order = Order(
                    customer=customer,
                    order_date=input.order_date,
                    total_amount=total_amount
                )
                order.save()


            return CreateOrder(
                order=order,
                message="Order created successfully!",
                success=True
            )

        except Exception as e:
            return CreateOrder(
                order=None,
                message=f"An error occurred: {str(e)}",
                success=False
            )
        
class UpdateLowStockProducts(graphene.Mutation):
    updated_count = graphene.Int()
    message = graphene.String()
    success = graphene.Boolean()

    def mutate(self, info):
        try:
            # Find products with stock less than 10
            low_stock_products = Product.objects.filter(stock__lt=10)
            count = low_stock_products.count()
            for product in low_stock_products:
                product.stock += 10  # Replenish stock by 20 units
                product.save()
            
            return UpdateLowStockProducts(
                updated_product_list=low_stock_products,
                updated_count=count,
                message=f"Updated {count} low stock products.",
                success=True
            )
        except Exception as e:
            return UpdateLowStockProducts(
                updated_count=0,
                message=f"An error occurred: {str(e)}",
                success=False
            )
        
# =================== Query class ====================

class Query(graphene.ObjectType):
    # Filtered Queries
    all_customers = DjangoFilterConnectionField(CustomerType)
    all_products = DjangoFilterConnectionField(ProductType)
    all_orders = DjangoFilterConnectionField(OrderType)
    # Custom filtered queries with ordering
    customers = graphene.List(
        CustomerType,
        filters=CustomerFilterInput(required=False),
        order_by=OrderByInput(required=False),
        description="Get customers with filtering and ordering"
    )
    
    products = graphene.List(
        ProductType,
        filters=ProductFilterInput(required=False),
        order_by=OrderByInput(required=False),
        description="Get products with filtering and ordering"
    )
    
    orders = graphene.List(
        OrderType,
        filters=OrderFilterInput(required=False),
        order_by=OrderByInput(required=False),
        description="Get orders with filtering and ordering"
    )
    
    # Search queries
    search_customers = graphene.List(
        CustomerType,
        search_term=graphene.String(required=True),
        description="Search customers by name, email, or phone"
    )
    
    available_products = graphene.List(
        ProductType,
        description="Get products that are in stock"
    )
    
    products_by_price_range = graphene.List(
        ProductType,
        min_price=Decimal(required=False),
        max_price=Decimal(required=False),
        description="Filter products by price range"
    )
    
    customer_orders = graphene.List(
        OrderType,
        customer_id=graphene.ID(required=True),
        status=graphene.String(required=False),
        description="Get orders for a specific customer"
    )
    
    high_value_orders = graphene.List(
        OrderType,
        min_amount=Decimal(required=True, default_value=Decimal('1000.00')),
        description="Get orders with total amount above specified value"
    )

    # Resolver methods for custom filtered queries
    def resolve_customers(self, info, filters=None, order_by=None):
        """Get customers with filtering and ordering"""
        queryset = Customer.objects.all()
        
        # Apply filters
        if filters:
            filter_args = {}
            if filters.name:
                filter_args['name__icontains'] = filters.name
            if filters.email:
                filter_args['email__icontains'] = filters.email
            if filters.created_at_gte:
                filter_args['created_at__gte'] = filters.created_at_gte
            if filters.created_at_lte:
                filter_args['created_at__lte'] = filters.created_at_lte
            if filters.phone_pattern:
                filter_args['phone__startswith'] = filters.phone_pattern
            
            queryset = queryset.filter(**filter_args)
        
        # Apply ordering
        if order_by:
            field = order_by.field
            if order_by.direction == "desc":
                field = f"-{field}"
            queryset = queryset.order_by(field)
        
        return queryset

    def resolve_products(self, info, filters=None, order_by=None):
        """Get products with filtering and ordering"""
        queryset = Product.objects.all()
        
        # Apply filters
        if filters:
            filter_args = {}
            if filters.name:
                filter_args['name__icontains'] = filters.name
            if filters.price_gte:
                filter_args['price__gte'] = filters.price_gte
            if filters.price_lte:
                filter_args['price__lte'] = filters.price_lte
            if filters.stock_gte:
                filter_args['stock__gte'] = filters.stock_gte
            if filters.stock_lte:
                filter_args['stock__lte'] = filters.stock_lte
            if filters.low_stock is not None:
                if filters.low_stock:
                    filter_args['stock__lt'] = 10
            
            queryset = queryset.filter(**filter_args)
        
        # Apply ordering
        if order_by:
            field = order_by.field
            if order_by.direction == "desc":
                field = f"-{field}"
            queryset = queryset.order_by(field)
        
        return queryset

    def resolve_orders(self, info, filters=None, order_by=None):
        """Get orders with filtering and ordering"""
        queryset = Order.objects.all()
        
        # Apply filters
        if filters:
            filter_args = {}
            if filters.total_amount_gte:
                filter_args['total_amount__gte'] = filters.total_amount_gte
            if filters.total_amount_lte:
                filter_args['total_amount__lte'] = filters.total_amount_lte
            if filters.order_date_gte:
                filter_args['order_date__gte'] = filters.order_date_gte
            if filters.order_date_lte:
                filter_args['order_date__lte'] = filters.order_date_lte
            if filters.customer_name:
                filter_args['customer__name__icontains'] = filters.customer_name
            if filters.product_id:
                filter_args['items__product__id'] = filters.product_id
            
            queryset = queryset.filter(**filter_args)
            
            # Handle product_name filter separately (requires distinct)
            if filters.product_name:
                queryset = queryset.filter(items__product__name__icontains=filters.product_name).distinct()
        
        # Apply ordering
        if order_by:
            field = order_by.field
            if order_by.direction == "desc":
                field = f"-{field}"
            queryset = queryset.order_by(field)
        
        return queryset

    # Existing resolver methods
    def resolve_search_customers(self, info, search_term):
        """Search customers by name, email, or phone"""
        if not search_term or len(search_term) < 2:
            return Customer.objects.none()
        
        return Customer.objects.filter(
            Q(name__icontains=search_term) |
            Q(email__icontains=search_term) |
            Q(phone__icontains=search_term)
        ).distinct()

    def resolve_available_products(self, info):
        """Get products that are in stock"""
        return Product.objects.filter(stock__gt=0)

    def resolve_products_by_price_range(self, info, min_price=None, max_price=None):
        """Filter products by price range"""
        queryset = Product.objects.all()
        
        if min_price is not None:
            queryset = queryset.filter(price__gte=min_price)
        
        if max_price is not None:
            queryset = queryset.filter(price__lte=max_price)
            
        return queryset

    def resolve_customer_orders(self, info, customer_id, status=None):
        """Get orders for a specific customer"""
        try:
            queryset = Order.objects.filter(customer_id=customer_id)
            
            if status:
                queryset = queryset.filter(status=status)
                
            return queryset.order_by('-order_date')
        except Customer.DoesNotExist:
            return Order.objects.none()

    def resolve_high_value_orders(self, info, min_amount):
        """Get orders with total amount above specified value"""
        return Order.objects.filter(
            total_amount__gte=min_amount
        ).order_by('-total_amount')


# Mutations
class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()

schema = graphene.Schema(mutation=Mutation)