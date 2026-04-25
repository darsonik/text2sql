-- Seed Data for Production Database

-- 1. Organizations
INSERT INTO organizations (name, slug) VALUES ('Tech Corp', 'tech-corp');
INSERT INTO organizations (name, slug) VALUES ('Retail Hub', 'retail-hub');

-- 2. Users
INSERT INTO users (organization_id, email, full_name, role) VALUES (1, 'admin@techcorp.com', 'Admin User', 'admin');
INSERT INTO users (organization_id, email, full_name, role) VALUES (1, 'john@techcorp.com', 'John Doe', 'user');
INSERT INTO users (organization_id, email, full_name, role) VALUES (2, 'sales@retailhub.com', 'Sales Manager', 'manager');

-- 3. Categories
INSERT INTO categories (organization_id, name) VALUES (1, 'Electronics');
INSERT INTO categories (organization_id, name, parent_id) VALUES (1, 'Laptops', 1);
INSERT INTO categories (organization_id, name, parent_id) VALUES (1, 'Smartphones', 1);
INSERT INTO categories (organization_id, name) VALUES (2, 'Clothing');
INSERT INTO categories (organization_id, name, parent_id) VALUES (2, 'Menswear', 4);

-- 4. Products
INSERT INTO products (organization_id, category_id, name, sku, price, stock_quantity) 
VALUES (1, 2, 'MacBook Pro 14', 'MBP-14-2023', 1999.99, 50);
INSERT INTO products (organization_id, category_id, name, sku, price, stock_quantity) 
VALUES (1, 3, 'iPhone 15 Pro', 'IPH-15-P', 999.00, 100);
INSERT INTO products (organization_id, category_id, name, sku, price, stock_quantity) 
VALUES (2, 5, 'Slim Fit Jeans', 'JEAN-SLIM-01', 59.50, 200);

-- 5. Orders
INSERT INTO orders (organization_id, user_id, status, total_amount) 
VALUES (1, 2, 'completed', 2998.99);
INSERT INTO orders (organization_id, user_id, status, total_amount) 
VALUES (2, 3, 'pending', 119.00);

-- 6. Order Items
INSERT INTO order_items (order_id, product_id, quantity, unit_price) 
VALUES (1, 1, 1, 1999.99);
INSERT INTO order_items (order_id, product_id, quantity, unit_price) 
VALUES (1, 2, 1, 999.00);
INSERT INTO order_items (order_id, product_id, quantity, unit_price) 
VALUES (2, 3, 2, 59.50);

-- 7. Payments
INSERT INTO payments (order_id, amount, payment_method, status, transaction_id) 
VALUES (1, 2998.99, 'credit_card', 'success', 'TXN-001');

-- 8. Audit Logs
INSERT INTO audit_logs (user_id, action, table_name, record_id, old_value, new_value) 
VALUES (1, 'INSERT', 'products', 1, NULL, '{"name": "MacBook Pro 14", "price": 1999.99}');
