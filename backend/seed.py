from database import get_db_connection
from main import create_tables


def seed_database():
    create_tables()

    connection = get_db_connection()
    cursor = connection.cursor()

    # Clear old test data
    cursor.execute("DELETE FROM bookings")
    cursor.execute("DELETE FROM resources")
    cursor.execute("DELETE FROM farmers")

    # Farmers
    farmers = [
        ("Raju", "Kattankulathur", "9876543210"),
        ("Suresh", "Potheri", "9876543211"),
        ("Arun", "Guduvanchery", "9876543212"),
    ]

    cursor.executemany("""
        INSERT INTO farmers (name, village, phone)
        VALUES (?, ?, ?)
    """, farmers)

    # Resources
    resources = [
        (
            "Mahindra Tractor",
            "tractor",
            1,
            "Kattankulathur",
            1,
            "unit",
            800,
            0,
            1,
            "available",
            12.8406,
            80.1534
        ),
        (
            "Swaraj Tractor",
            "tractor",
            2,
            "Potheri",
            1,
            "unit",
            750,
            0,
            1,
            "available",
            12.8236,
            80.0458
        ),
        (
            "John Deere Tractor",
            "tractor",
            3,
            "Guduvanchery",
            1,
            "unit",
            900,
            0,
            1,
            "available",
            12.8468,
            80.0607
        ),
        (
            "Solar Water Pump",
            "solar_pump",
            1,
            "Kattankulathur",
            2,
            "unit",
            500,
            0,
            1,
            "available",
            12.8406,
            80.1534
        ),
        (
            "Rice Seeds",
            "seed",
            2,
            "Potheri",
            100,
            "kg",
            0,
            50,
            1,
            "available",
            12.8236,
            80.0458
        ),
        (
            "Wheat Seeds",
            "seed",
            3,
            "Guduvanchery",
            50,
            "kg",
            0,
            45,
            1,
            "available",
            12.8468,
            80.0607
        )
    ]

    cursor.executemany("""
        INSERT INTO resources (
            name,
            resource_type,
            owner_id,
            village,
            quantity,
            unit,
            price_per_hour,
            price_per_unit,
            available,
            status,
            latitude,
            longitude
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, resources)

    connection.commit()
    connection.close()

    print("Database seeded successfully.")


if __name__ == "__main__":
    seed_database()
    