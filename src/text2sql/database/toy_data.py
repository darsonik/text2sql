from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    String,
    Integer,
    select,
    ForeignKey,
    text
)

engine = create_engine("sqlite:///src/text2sql/database/toy_data.db")
metadata = MetaData()

table_name = "city_stats"
city_stats_table = Table(
    table_name,
    metadata,
    Column("city_name", String, primary_key=True),
    Column("population", Integer),
    Column("country", String, nullable=False),
)

# New table definition
average_income_table = Table(
    "average_income",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),  # Optional: Unique ID
    Column("city_name", String, ForeignKey("city_stats.city_name")),  # Foreign key to city_stats
    Column("average_income", Integer),
    Column("year", Integer),
)

def create_toy_data():
    """Create toy data in the in-memory SQLite database."""
    metadata.create_all(engine)  # This will create both tables
    with engine.connect() as conn:
        # Insert data into city_stats (existing)
        conn.execute(
            city_stats_table.insert(),
            [
                {"city_name": "New York", "population": 8419000, "country": "USA"},
                {"city_name": "Los Angeles", "population": 3980000, "country": "USA"},
                {"city_name": "Chicago", "population": 2716000, "country": "USA"},
                {"city_name": "Houston", "population": 2328000, "country": "USA"},
                {"city_name": "Phoenix", "population": 1690000, "country": "USA"},
            ],
        )
       
        # Insert data into average_income (new)
        conn.execute(
            average_income_table.insert(),
            [
                {"city_name": "New York", "average_income": 75000, "year": 2023},
                {"city_name": "Los Angeles", "average_income": 65000, "year": 2023},
                {"city_name": "Chicago", "average_income": 60000, "year": 2023},
                {"city_name": "Houston", "average_income": 55000, "year": 2023},
                {"city_name": "Phoenix", "average_income": 50000, "year": 2023},
            ],
        )
        
        conn.commit()

def view_data():
    """View data from the toy database."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM city_stats"))
        print("City Stats:")
        for row in result:
            print(row)

        result = conn.execute(text("SELECT * FROM average_income"))
        print("\nAverage Income:")
        for row in result:
            print(row)

if __name__ == "__main__":
    # create_toy_data()
    view_data()