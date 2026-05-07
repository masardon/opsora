"""
Sample Data Generator

Generates realistic sample business data for demo and testing purposes.
"""

import random
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class SaleEvent:
    """Sample sale event"""
    customer_id: str
    product_id: str
    revenue: float
    quantity: int
    channel: str
    timestamp: str


@dataclass
class OperationEvent:
    """Sample operation event"""
    inventory_level: int
    product_id: str
    warehouse_id: str
    fulfillment_time_hours: float
    timestamp: str


@dataclass
class CustomerEvent:
    """Sample customer event"""
    customer_id: str
    event_type: str
    satisfaction_score: int
    nps_score: int
    timestamp: str


@dataclass
class RevenueEvent:
    """Sample revenue event"""
    revenue_type: str
    amount: float
    arr: float
    timestamp: str


class SampleDataGenerator:
    """Generates sample business data"""

    def __init__(self, seed: int = 42):
        random.seed(seed)

        # Sample data pools
        self.customers = [f"cust_{i:04d}" for i in range(1, 501)]
        self.products = [f"prod_{i:04d}" for i in range(1, 101)]
        self.warehouses = [f"wh_{i}" for i in range(1, 6)]
        self.channels = ["online", "store", "phone", "mobile"]

        # Product categories with different price ranges
        self.product_categories = {}
        for i, product in enumerate(self.products):
            category = i % 5
            if category == 0:
                base_price = random.uniform(50, 150)
            elif category == 1:
                base_price = random.uniform(200, 500)
            elif category == 2:
                base_price = random.uniform(1000, 3000)
            elif category == 3:
                base_price = random.uniform(20, 80)
            else:
                base_price = random.uniform(500, 1500)

            self.product_categories[product] = {
                "category": category,
                "base_price": base_price,
            }

    def generate_sale_events(
        self,
        count: int = 1000,
        days: int = 90,
        trend: float = 0.01
    ) -> List[SaleEvent]:
        """Generate sample sale events"""

        events = []
        base_time = datetime.utcnow()

        # Add trend and seasonality
        for i in range(count):
            days_ago = random.randint(0, days)
            timestamp = base_time - timedelta(days=days_ago, hours=random.randint(0, 23))

            # Trend component
            trend_factor = 1 + (trend * (days - days_ago) / days)

            # Seasonality (weekly pattern)
            day_of_week = timestamp.weekday()
            seasonality = 1 + 0.2 * random.sin(2 * 3.14159 * day_of_week / 7)

            customer_id = random.choice(self.customers)
            product_id = random.choice(self.products)
            channel = random.choice(self.channels)

            # Calculate revenue with trend and seasonality
            base_price = self.product_categories[product_id]["base_price"]
            quantity = random.choices([1, 2, 3, 4, 5], weights=[60, 25, 10, 4, 1])[0]
            revenue = base_price * quantity * trend_factor * seasonality * random.uniform(0.9, 1.1)

            events.append(SaleEvent(
                customer_id=customer_id,
                product_id=product_id,
                revenue=round(revenue, 2),
                quantity=quantity,
                channel=channel,
                timestamp=timestamp.isoformat(),
            ))

        return sorted(events, key=lambda x: x.timestamp)

    def generate_operation_events(
        self,
        count: int = 1000,
        days: int = 90
    ) -> List[OperationEvent]:
        """Generate sample operation events"""

        events = []
        base_time = datetime.utcnow()

        # Product inventory levels
        inventory_levels = {p: random.randint(500, 5000) for p in self.products}

        for i in range(count):
            days_ago = random.randint(0, days)
            timestamp = base_time - timedelta(days=days_ago, hours=random.randint(0, 23))

            product_id = random.choice(self.products)
            warehouse_id = random.choice(self.warehouses)

            # Simulate inventory changes
            change = random.randint(-50, 50)
            inventory_levels[product_id] = max(100, min(10000, inventory_levels[product_id] + change))

            # Fulfillment time with some randomness
            fulfillment_time = random.uniform(12, 72) + random.gauss(0, 10)

            events.append(OperationEvent(
                inventory_level=max(0, inventory_levels[product_id]),
                product_id=product_id,
                warehouse_id=warehouse_id,
                fulfillment_time_hours=round(max(1, fulfillment_time), 2),
                timestamp=timestamp.isoformat(),
            ))

        return sorted(events, key=lambda x: x.timestamp)

    def generate_customer_events(
        self,
        count: int = 500,
        days: int = 90
    ) -> List[CustomerEvent]:
        """Generate sample customer events"""

        events = []
        base_time = datetime.utcnow()

        for i in range(count):
            days_ago = random.randint(0, days)
            timestamp = base_time - timedelta(days=days_ago, hours=random.randint(0, 23))

            customer_id = random.choice(self.customers)
            event_type = random.choice(["login", "purchase", "support", "review"])

            # Satisfaction scores (mostly positive)
            satisfaction = random.choices(
                [1, 2, 3, 4, 5],
                weights=[5, 5, 20, 40, 30]
            )[0] if random.random() > 0.3 else None

            # NPS scores
            nps = random.randint(0, 10) if random.random() > 0.5 else None

            events.append(CustomerEvent(
                customer_id=customer_id,
                event_type=event_type,
                satisfaction_score=satisfaction,
                nps_score=nps,
                timestamp=timestamp.isoformat(),
            ))

        return sorted(events, key=lambda x: x.timestamp)

    def generate_revenue_events(
        self,
        count: int = 300,
        days: int = 90,
        mrr_growth: float = 0.05
    ) -> List[RevenueEvent]:
        """Generate sample revenue events"""

        events = []
        base_time = datetime.utcnow()
        base_mrr = 75000

        for i in range(count):
            days_ago = random.randint(0, days)
            timestamp = base_time - timedelta(days=days_ago, hours=random.randint(0, 23))

            # Revenue type distribution
            revenue_type = random.choices(
                ["recurring", "one_time", "expansion", "churn"],
                weights=[50, 25, 15, 10]
            )[0]

            # Calculate amount based on type
            if revenue_type == "recurring":
                amount = random.uniform(500, 2000)
            elif revenue_type == "one_time":
                amount = random.uniform(1000, 10000)
            elif revenue_type == "expansion":
                amount = random.uniform(500, 5000)
            else:  # churn
                amount = -random.uniform(500, 2000)

            # ARR with growth trend
            growth_factor = 1 + (mrr_growth * (days - days_ago) / days)
            arr = base_mrr * 12 * growth_factor

            events.append(RevenueEvent(
                revenue_type=revenue_type,
                amount=round(amount, 2),
                arr=round(arr, 2),
                timestamp=timestamp.isoformat(),
            ))

        return sorted(events, key=lambda x: x.timestamp)

    def generate_all_events(
        self,
        sales_count: int = 1000,
        operations_count: int = 1000,
        customer_count: int = 500,
        revenue_count: int = 300,
        days: int = 90
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Generate all event types"""

        return {
            "sales": [asdict(e) for e in self.generate_sale_events(sales_count, days)],
            "operations": [asdict(e) for e in self.generate_operation_events(operations_count, days)],
            "customers": [asdict(e) for e in self.generate_customer_events(customer_count, days)],
            "revenue": [asdict(e) for e in self.generate_revenue_events(revenue_count, days)],
        }

    def save_to_json(self, events: Dict[str, List[Dict[str, Any]]], output_dir: str = "."):
        """Save events to JSON files"""

        import os
        os.makedirs(output_dir, exist_ok=True)

        for event_type, event_list in events.items():
            filepath = os.path.join(output_dir, f"{event_type}_events.json")
            with open(filepath, "w") as f:
                json.dump(event_list, f, indent=2, default=str)

            print(f"Saved {len(event_list)} {event_type} events to {filepath}")

    def generate_csv(self, events: Dict[str, List[Dict[str, Any]]], output_dir: str = "."):
        """Save events to CSV files"""

        import os
        import pandas as pd

        os.makedirs(output_dir, exist_ok=True)

        for event_type, event_list in events.items():
            df = pd.DataFrame(event_list)
            filepath = os.path.join(output_dir, f"{event_type}_events.csv")
            df.to_csv(filepath, index=False)

            print(f"Saved {len(event_list)} {event_type} events to {filepath}")


def main():
    """Main function to generate sample data"""

    generator = SampleDataGenerator()

    print("Generating sample business data...")

    events = generator.generate_all_events(
        sales_count=1000,
        operations_count=1000,
        customer_count=500,
        revenue_count=300,
        days=90
    )

    # Summary
    print("\n=== Generated Events ===")
    for event_type, event_list in events.items():
        print(f"{event_type.title()}: {len(event_list)} events")

    # Save to files
    output_dir = "sample_data"
    generator.save_to_json(events, output_dir)
    generator.generate_csv(events, output_dir)

    print(f"\nSample data saved to '{output_dir}/' directory")

    # Print some sample events
    print("\n=== Sample Events ===")
    for event_type, event_list in events.items():
        if event_list:
            print(f"\n{event_type.upper()}:")
            print(json.dumps(event_list[0], indent=2))


if __name__ == "__main__":
    main()
