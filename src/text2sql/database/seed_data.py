from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from text2sql.database.models import (
    Base, Organization, User, Category, Product, Order, OrderItem, Payment, AuditLog
)
from datetime import datetime

# Database setup
DB_PATH = "/home/tuhinkarmakar/Repositories/text2sql/src/text2sql/database/production.db"
ENGINE_URL = f"sqlite:///{DB_PATH}"

def seed_data():
    """Seed the database with realistic test data."""
    print("Seeding database...")
    engine = create_engine(ENGINE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. Create Organizations
        tech_corp = Organization(name="Tech Corp", slug="tech-corp")
        retail_hub = Organization(name="Retail Hub", slug="retail-hub")
        session.add_all([tech_corp, retail_hub])
        session.flush() # To get IDs

        # 2. Create Users
        admin = User(organization_id=tech_corp.id, email="admin@techcorp.com", full_name="Admin User", role="admin")
        john = User(organization_id=tech_corp.id, email="john@techcorp.com", full_name="John Doe", role="user")
        sales = User(organization_id=retail_hub.id, email="sales@retailhub.com", full_name="Sales Manager", role="manager")
        session.add_all([admin, john, sales])
        session.flush()

        # 3. Create Categories
        electronics = Category(organization_id=tech_corp.id, name="Electronics")
        session.add(electronics)
        session.flush()

        laptops = Category(organization_id=tech_corp.id, name="Laptops", parent_id=electronics.id)
        phones = Category(organization_id=tech_corp.id, name="Smartphones", parent_id=electronics.id)
        clothing = Category(organization_id=retail_hub.id, name="Clothing")
        session.add_all([laptops, phones, clothing])
        session.flush()

        # 4. Create Products
        macbook = Product(
            organization_id=tech_corp.id, category_id=laptops.id, 
            name="MacBook Pro 14", sku="MBP-14-2023", price=1999.99, stock_quantity=50
        )
        iphone = Product(
            organization_id=tech_corp.id, category_id=phones.id, 
            name="iPhone 15 Pro", sku="IPH-15-P", price=999.00, stock_quantity=100
        )
        jeans = Product(
            organization_id=retail_hub.id, category_id=clothing.id, 
            name="Slim Fit Jeans", sku="JEAN-SLIM-01", price=59.50, stock_quantity=200
        )
        session.add_all([macbook, iphone, jeans])
        session.flush()

        # 5. Create Order
        order1 = Order(organization_id=tech_corp.id, user_id=john.id, status="completed", total_amount=2998.99)
        session.add(order1)
        session.flush()

        # 6. Order Items
        item1 = OrderItem(order_id=order1.id, product_id=macbook.id, quantity=1, unit_price=1999.99)
        item2 = OrderItem(order_id=order1.id, product_id=iphone.id, quantity=1, unit_price=999.00)
        session.add_all([item1, item2])

        # 7. Payment
        payment1 = Payment(
            order_id=order1.id, amount=2998.99, payment_method="credit_card", 
            status="success", transaction_id="TXN-001"
        )
        session.add(payment1)

        # 8. Audit Log
        log1 = AuditLog(
            user_id=admin.id, action="INSERT", table_name="products", 
            record_id=macbook.id, new_value='{"name": "MacBook Pro 14", "price": 1999.99}'
        )
        session.add(log1)

        session.commit()
        print("Database seeded successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error seeding database: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    seed_data()
