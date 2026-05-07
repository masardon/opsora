"""
Sample Data Generator for Indonesian Fried Chicken QSR Platform

This generates realistic sample data for a food & beverages ordering demo
inspired by Indonesian market trends and pricing.
"""

import random
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dataclasses import dataclass, asdict


# Indonesian Rupiah formatting
def format_idr(amount: int) -> str:
    """Format amount as Indonesian Rupiah"""
    return f"Rp{amount:,}".replace(",", ".")


@dataclass
class MenuItem:
    """Menu item for the restaurant"""
    item_id: str
    name: str
    name_en: str
    category: str  # chicken, sides, beverages, combos, promotions
    price_idr: int
    price_with_tax: int
    description: str
    is_available: bool
    spice_level: int  # 0-5
    calories: int


@dataclass
class StoreLocation:
    """Store location in Indonesia"""
    store_id: str
    name: str
    city: str
    address: str
    latitude: float
    longitude: float
    is_open: bool
    open_time: str
    close_time: str


@dataclass
class Order:
    """Customer order"""
    order_id: str
    customer_id: str
    store_id: str
    channel: str  # app, web, grabfood, gofood, dinein, takeaway
    order_type: str  # delivery, dine-in, takeaway, drive-thru
    items: List[Dict[str, Any]]
    subtotal_idr: int
    tax_idr: int
    delivery_fee_idr: int
    total_idr: int
    payment_method: str
    order_status: str  # pending, preparing, ready, picked_up, delivered, cancelled
    order_timestamp: str
    preparation_time_minutes: int


@dataclass
class Customer:
    """Customer data"""
    customer_id: str
    name: str
    phone: str
    email: Optional[str]
    city: str
    registration_date: str
    total_orders: int
    total_spent_idr: int
    favorite_channel: str
    segment: str  # regular, occasional, heavy_user, price_sensitive


class IndonesianQSRDataGenerator:
    """Generate sample data for Indonesian Fried Chicken QSR Platform"""

    def __init__(self, seed: int = 42):
        random.seed(seed)

        # Indonesian cities with coordinates
        self.cities = {
            "Jakarta": (-6.2088, 106.8456),
            "Surabaya": (-7.2575, 112.7521),
            "Bandung": (-6.9175, 107.6191),
            "Medan": (3.5952, 98.6722),
            "Semarang": (-6.9667, 110.4281),
            "Makassar": (-5.1477, 119.4328),
            "Denpasar": (-8.6705, 115.2126),
            "Palembang": (-2.9761, 104.7758),
        }

        # Menu items inspired by Indonesian market (2024 pricing)
        self.menu_items = self._generate_menu()

        # Customer data pools
        self.names = [
            "Budi Santoso", "Siti Aminah", "Ahmad Wijaya", "Dewi Lestari",
            "Andi Pratama", "Rina Melati", "Joko Widodo", "Putri Ayu",
            "Rizky Ramadhan", "Maya Sari", "Doni Prasetyo", "Lina Marlina",
            "Hendra Gunawan", "Fitri Handayani", "Bayu Nugroho", "Siska Umami",
        ]

        # Order channels
        self.channels = {
            "app": 0.35,        # Official mobile app
            "web": 0.15,         # Website ordering
            "grabfood": 0.25,   # GrabFood app
            "gofood": 0.20,      # GoFood app
            "dine-in": 0.03,      # In-restaurant
            "takeaway": 0.02,    # Pick up
        }

        # Order types
        self.order_types = {
            "delivery": 0.60,
            "takeaway": 0.25,
            "dine-in": 0.10,
            "drive-thru": 0.05,
        }

        # Payment methods
        self.payment_methods = {
            "gopay": 0.35,
            "ovo": 0.30,
            "dana": 0.15,
            "shopeepay": 0.10,
            "cash": 0.05,
            "credit_card": 0.05,
        }

    def _generate_menu(self) -> List[MenuItem]:
        """Generate menu items with realistic pricing"""
        return [
            # Chicken Items
            MenuItem("CHK001", "Ayam Potong 9", "9 pcs Fried Chicken", "chicken",
                   186000, 199920, "Crispy fried chicken, signature recipe", True, 0, 2500),
            MenuItem("CHK002", "Ayam Potong 5", "5 pcs Fried Chicken", "chicken",
                   117000, 125190, "Crispy fried chicken, signature recipe", True, 0, 1380),
            MenuItem("CHK003", "Ayam Potong 3", "3 pcs Fried Chicken", "chicken",
                   71000, 76070, "Crispy fried chicken, signature recipe", True, 0, 830),
            MenuItem("CHK004", "Winger Bucket 7", "7 pcs Wings", "chicken",
                   110000, 117700, "Spicy chicken wings", True, 2, 1650),
            MenuItem("CHK005", "Strip 5", "5 pcs Chicken Strips", "chicken",
                   82000, 87820, "Breaded chicken strips with dipping sauce", True, 1, 1200),
            MenuItem("CHK006", "Popcorn Chicken 6", "6 pcs Popcorn Chicken", "chicken",
                   65000, 69550, "Bite-sized popcorn chicken", True, 0, 1100),

            # Combo Meals
            MenuItem("CMB001", "Paket Komplit 1", "Combo Meal 1", "combos",
                   49000, 52430, "3 chicken + 1 rice + 1 drink + 1 coleslaw", True, 0, 1850),
            MenuItem("CMB002", "Paket Komplit 2", "Combo Meal 2", "combos",
                   68000, 72760, "5 chicken + 2 rice + 2 drinks + 1 coleslaw", True, 0, 2800),
            MenuItem("CMB003", "Paket Komplit 3", "Combo Meal 3", "combos",
                   105000, 112350, "9 chicken + 3 rice + 3 drinks + 2 sides", True, 0, 4500),
            MenuItem("CMB004", "Family Bucket 12", "Family Bucket", "combos",
                   245000, 262150, "12 chicken + 4 rice + 4 drinks + 2 sides", True, 0, 11000),
            MenuItem("CMB005", "Party Bucket 20", "Party Bucket", "combos",
                   410000, 438700, "20 chicken + 6 rice + 6 drinks + 4 sides", True, 0, 18000),

            # Sides
            MenuItem("SID001", "Nasi Uduk", "Steamed Rice", "sides",
                   15000, 16050, "Fragrant steamed rice", True, 0, 200),
            MenuItem("SID002", "Coleslaw", "Coleslaw Salad", "sides",
                   12000, 12840, "Fresh vegetable salad with creamy dressing", True, 0, 180),
            MenuItem("SID003", "Mashed Potato", "Mashed Potato", "sides",
                   15000, 16050, "Creamy mashed potato with gravy", True, 0, 220),
            MenuItem("SID004", "Fries", "French Fries", "sides",
                   18000, 19260, "Crispy golden fries", True, 0, 320),
            MenuItem("SID005", "Corn Cupet", "Corn Casserole", "sides",
                   10000, 10700, "Baked corn casserole", True, 0, 150),
            MenuItem("SID006", "Bread & Butter", "Garlic Bread", "sides",
                   18000, 19260, "Toasted garlic bread", True, 0, 350),

            # Beverages
            MenuItem("BEV001", "Aneka Es Teh", "Iced Tea", "beverages",
                   10000, 10700, "Refreshing ice tea", True, 0, 50),
            MenuItem("BEV002", "Lemon Tea", "Iced Lemon Tea", "beverages",
                   12000, 12840, "Fresh lemon tea", True, 0, 60),
            MenuItem("BEV003", "Fizz Royal", "Orange Float", "beverages",
                   18000, 19260, "Orange soda with ice cream float", True, 0, 180),
            MenuItem("BEV004", "Cola", "Coca-Cola", "beverages",
                   15000, 16050, "Classic cola", True, 0, 140),
            MenuItem("BEV005", "Aqua", "Mineral Water", "beverages",
                   8000, 8560, "Mineral water 600ml", True, 0, 0),
            MenuItem("BEV006", "MILO Iced", "Chocolate Malt", "beverages",
                   22000, 23540, "Chocolate malt beverage - new product", True, 0, 200),

            # Promotional Items
            MenuItem("PROM01", "Paket Berlimpah", "Loyalty Reward", "promotions",
                   29000, 31030, "Special price for loyal customers - limited time", True, 0, 1500),
            MenuItem("PROM02", "Happy Hour Set", "Happy Hour Menu", "promotions",
                   35000, 37450, "3 chicken + 1 drink during 14-17pm", True, 0, 1800),
        ]

    def generate_stores(self, count: int = 50) -> List[StoreLocation]:
        """Generate store locations across major Indonesian cities"""
        stores = []

        city_distribution = {
            "Jakarta": 15,
            "Surabaya": 8,
            "Bandung": 7,
            "Medan": 5,
            "Semarang": 4,
            "Makassar": 4,
            "Denpasar": 3,
            "Palembang": 4,
        }

        store_num = 1
        for city, coords in self.cities.items():
            num_stores = city_distribution.get(city, 1)

            for i in range(num_stores):
                # Generate realistic address
                street_names = ["Jl. Jendral Sudirman", "Jl. Gatot Subroto", "Jl. Basuki Rahmat",
                              "Jl. MH. Thamrin", "Jl. Sudirman", "Jl. Asia Afrika", "Jl. Ahmad Yani"]

                store = StoreLocation(
                    store_id=f"STR{store_num:03d}",
                    name=f"{city} Mall #{i+1}",
                    city=city,
                    address=f"{random.choice(street_names)} No. {random.randint(1, 200)}, {city}",
                    latitude=coords[0] + random.uniform(-0.1, 0.1),
                    longitude=coords[1] + random.uniform(-0.1, 0.1),
                    is_open=random.choice([True, True, True, True, False]),  # Mostly open
                    open_time="08:00",
                    close_time="22:00",
                )
                stores.append(store)
                store_num += 1

        return stores

    def generate_customers(self, count: int = 500) -> List[Customer]:
        """Generate customer data"""
        customers = []

        for i in range(count):
            customer = Customer(
                customer_id=f"CUST{i:06d}",
                name=self.names[i % len(self.names)],
                phone=f"+62{random.choice(['812', '857', '856', '811', '821'])}{random.randint(10000000, 99999999)}",
                email=f"customer{i+1}@email.com" if random.random() > 0.3 else None,
                city=random.choice(list(self.cities.keys())),
                registration_date=(datetime.now() - timedelta(days=random.randint(30, 365))).isoformat(),
                total_orders=random.randint(1, 50),
                total_spent_idr=random.randint(100000, 5000000),
                favorite_channel=random.choice(list(self.channels.keys())),
                segment=random.choice(["regular", "occasional", "heavy_user", "price_sensitive"]),
            )
            customers.append(customer)

        return customers

    def generate_orders(
        self,
        count: int = 1000,
        days: int = 30,
        stores: List[StoreLocation] = None,
        customers: List[Customer] = None
    ) -> List[Order]:
        """Generate realistic order data"""

        if stores is None:
            stores = self.generate_stores()

        if customers is None:
            customers = self.generate_customers(min(count, len(customers)))

        orders = []
        base_time = datetime.now()

        # Peak hours patterns
        peak_hours = [11, 12, 13, 18, 19, 20]  # Lunch and dinner peaks
        off_peak = [10, 14, 15, 16, 17, 21]

        for i in range(count):
            # Order time - more orders during peak hours
            hour_weights = peak_hours * 5 + off_peak * 1
            hour = random.choices(list(range(24)) + hour_weights)[0]

            days_ago = random.randint(0, days - 1)
            order_time = base_time - timedelta(days=days_ago, hours=random.randint(0, 23))
            order_time = order_time.replace(hour=hour)

            # Select customer (weighted toward loyal customers)
            customer = random.choices(customers, weights=[c.total_orders for c in customers])[0]

            # Select store (biased toward customer's city)
            city_stores = [s for s in stores if s.city == customer.city]
            store = random.choice(city_stores if city_stores else stores)

            # Select order channel
            channel = random.choices(
                list(self.channels.keys()),
                weights=[self.channels[ch] for ch in self.channels]
            )[0]

            # Select order type
            order_type = random.choices(
                list(self.order_types.keys()),
                weights=[self.order_types[ot] for ot in self.order_types]
            )[0]

            # Generate order items
            items = self._generate_order_items()

            # Calculate totals
            subtotal = sum(item['price'] for item in items)
            tax = int(subtotal * 0.11)  # 11% tax
            delivery_fee = 15000 if order_type == "delivery" else 0
            total = subtotal + tax + delivery_fee

            # Payment method
            payment = random.choices(
                list(self.payment_methods.keys()),
                weights=[self.payment_methods[p] for p in self.payment_methods]
            )[0]

            # Preparation time
            base_prep_time = 15  # minutes
            prep_time = base_prep_time + len(items) * 2
            if order_type == "delivery":
                prep_time += 10

            order = Order(
                order_id=f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{i:04d}",
                customer_id=customer.customer_id,
                store_id=store.store_id,
                channel=channel,
                order_type=order_type,
                items=items,
                subtotal_idr=subtotal,
                tax_idr=tax,
                delivery_fee_idr=delivery_fee,
                total_idr=total,
                payment_method=payment,
                order_status=random.choice([
                    "completed", "completed", "completed", "completed",
                    "cancelled", "completed"  # Mostly completed
                ]),
                order_timestamp=order_time.isoformat(),
                preparation_time_minutes=prep_time,
            )
            orders.append(order)

        return sorted(orders, key=lambda x: x.order_timestamp)

    def _generate_order_items(self) -> List[Dict[str, Any]]:
        """Generate items for an order"""
        # Select 1-4 items
        num_items = random.choices([1, 2, 3, 4], weights=[20, 40, 30, 10])[0]

        # Always include at least one chicken item
        chicken_items = [m for m in self.menu_items if m.category == "chicken"]
        first_item = random.choice(chicken_items)
        items = [{
            "item_id": first_item.item_id,
            "name": first_item.name,
            "name_en": first_item.name_en,
            "quantity": 1,
            "price": first_item.price_with_tax,
        }]

        # Add more items
        for _ in range(num_items - 1):
            # Weight toward chicken and combos
            item = random.choices(
                self.menu_items,
                weights=[
                    20 if m.category == "chicken" else
                    15 if m.category == "combos" else
                    10 if m.category == "sides" else
                    5 if m.category == "beverages" else 1
                    for m in self.menu_items
                ]
            )[0]

            items.append({
                "item_id": item.item_id,
                "name": item.name,
                "name_en": item.name_en,
                "quantity": random.randint(1, 2),
                "price": item.price_with_tax,
            })

        return items

    def generate_analytics_summary(self, orders: List[Order]) -> Dict[str, Any]:
        """Generate analytics summary from orders"""

        total_revenue = sum(o.total_idr for o in orders if o.order_status == "completed")
        total_orders = len(orders)

        # Channel breakdown
        channel_counts = {}
        for order in orders:
            channel = order.channel
            channel_counts[channel] = channel_counts.get(channel, 0) + 1

        # Hourly distribution
        hourly_orders = {}
        for order in orders:
            hour = datetime.fromisoformat(order.order_timestamp).hour
            hourly_orders[hour] = hourly_orders.get(hour, 0) + 1

        # Popular items
        item_counts = {}
        for order in orders:
            for item in order.items:
                item_counts[item['name']] = item_counts.get(item['name'], 0) + item['quantity']

        popular_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "total_revenue_idr": total_revenue,
            "total_orders": total_orders,
            "average_order_value": total_revenue / total_orders if total_orders > 0 else 0,
            "channel_distribution": channel_counts,
            "peak_hours": sorted(hourly_orders.items(), key=lambda x: x[1], reverse=True)[:5],
            "popular_items": popular_items,
        }

    def export_all_data(self, output_dir: str = "qsar_sample_data") -> Dict[str, str]:
        """Export all sample data to files"""
        import os

        os.makedirs(output_dir, exist_ok=True)

        # Generate data
        stores = self.generate_stores(50)
        customers = self.generate_customers(500)
        orders = self.generate_orders(1000, days=30, stores=stores, customers=customers)
        analytics = self.generate_analytics_summary(orders)

        # Convert to JSON-serializable format
        stores_json = [asdict(s) for s in stores]
        customers_json = [asdict(c) for c in customers]
        orders_json = [asdict(o) for o in orders]
        menu_json = [asdict(m) for m in self.menu_items]

        # Write files
        with open(f"{output_dir}/stores.json", "w") as f:
            json.dump(stores_json, f, indent=2, default=str)

        with open(f"{output_dir}/customers.json", "w") as f:
            json.dump(customers_json, f, indent=2, default=str)

        with open(f"{output_dir}/orders.json", "w") as f:
            json.dump(orders_json, f, indent=2, default=str)

        with open(f"{output_dir}/menu.json", "w") as f:
            json.dump(menu_json, f, indent=2)

        with open(f"{output_dir}/analytics_summary.json", "w") as f:
            json.dump(analytics, f, indent=2)

        return {
            "stores": f"{output_dir}/stores.json",
            "customers": f"{output_dir}/customers.json",
            "orders": f"{output_dir}/orders.json",
            "menu": f"{output_dir}/menu.json",
            "analytics": f"{output_dir}/analytics_summary.json",
        }

    def generate_ingestion_events(self, orders: List[Order]) -> List[Dict[str, Any]]:
        """Generate events for data ingestion pipeline"""

        events = []

        for order in orders:
            # Create order event
            events.append({
                "event_id": f"evt_order_{order.order_id}",
                "event_type": "sale",
                "domain": "sales",
                "event_timestamp": order.order_timestamp,
                "data": {
                    "order_id": order.order_id,
                    "customer_id": order.customer_id,
                    "store_id": order.store_id,
                    "channel": order.channel,
                    "order_type": order.order_type,
                    "total_idr": order.total_idr,
                    "items": order.items,
                    "payment_method": order.payment_method,
                },
            })

            # Create customer event
            if random.random() > 0.7:  # 30% chance
                events.append({
                    "event_id": f"evt_cust_{order.order_id}",
                    "event_type": "customer",
                    "domain": "customer",
                    "event_timestamp": order.order_timestamp,
                    "data": {
                        "customer_id": order.customer_id,
                        "event_type": "purchase" if order.order_status == "completed" else "support",
                        "satisfaction_score": random.choices([4, 5], weights=[60, 40])[0] if random.random() > 0.2 else None,
                    },
                })

        return events


def main():
    """Generate and export sample QSR data"""
    generator = IndonesianQSRDataGenerator()

    print("🍗 Generating Indonesian Fried Chicken QSR Sample Data\n")

    # Export all data
    print("Generating and exporting data...")
    files = generator.export_all_data("qsar_sample_data")

    print("\n✅ Sample Data Generated Successfully!")
    print(f"📁 Output Directory: qsar_sample_data/")
    print(f"\nFiles Created:")

    for name, path in files.items():
        size = os.path.getsize(path) if os.path.exists(path) else 0
        print(f"  • {name:15} ({size:,} bytes)")

    # Generate ingestion events
    with open(files["customers"], "r") as f:
        customers = json.load(f)

    with open(files["orders"], "r") as f:
        orders = json.load(f)

    with open(files["stores"], "r") as f:
        stores = json.load(f)

    events = generator.generate_ingestion_events(
        [Order(**o) for o in orders],
    )

    with open("qsar_sample_data/ingestion_events.json", "w") as f:
        json.dump(events, f, indent=2, default=str)

    print(f"  • ingestion_events: ({len(events):,} bytes)")

    # Print summary
    with open(files["analytics"], "r") as f:
        data = json.load(f)

    print(f"\n📊 Analytics Summary:")
    print(f"  • Total Orders: {data['total_orders']:,}")
    print(f"  • Total Revenue: {format_idr(data['total_revenue_idr'])}")
    print(f"  • Avg Order Value: {format_idr(int(data['average_order_value']))}")
    print(f"  • Channels: {', '.join(f'{k} ({v} orders)' for k, v in data['channel_distribution'].items())}")

    print(f"\n🍔 Menu Items: {len(generator.menu_items)}")
    print(f"🏪 Store Locations: {len(stores)}")
    print(f"👥 Customers: {len(customers)}")

    print(f"\n🚀 Ready to import into Opsora!")
    print(f"   Use these events to test your ingestion pipeline.")


if __name__ == "__main__":
    import os
    main()
