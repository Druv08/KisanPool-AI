from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from database import get_db_connection

app = FastAPI(title="KisanPool API")


# -------------------------
# Database setup
# -------------------------

def create_tables():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS farmers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            village TEXT NOT NULL,
            phone TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            owner_id INTEGER,
            village TEXT NOT NULL,
            quantity REAL DEFAULT 0,
            unit TEXT DEFAULT 'unit',
            price_per_hour REAL DEFAULT 0,
            price_per_unit REAL DEFAULT 0,
            available INTEGER DEFAULT 1,
            available_from TEXT,
            available_until TEXT,
            status TEXT DEFAULT 'available',
            latitude REAL,
            longitude REAL,
            FOREIGN KEY (owner_id) REFERENCES farmers(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id INTEGER NOT NULL,
            resource_id INTEGER NOT NULL,
            booking_date TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            quantity REAL DEFAULT 1,
            total_cost REAL DEFAULT 0,
            status TEXT DEFAULT 'confirmed',
            FOREIGN KEY (farmer_id) REFERENCES farmers(id),
            FOREIGN KEY (resource_id) REFERENCES resources(id)
        )
    """)

    connection.commit()
    connection.close()


create_tables()


# -------------------------
# Request model
# -------------------------

class BookingRequest(BaseModel):
    farmer_id: int
    resource_id: int
    booking_date: str
    start_time: str
    end_time: str
    quantity: float = 1


# -------------------------
# Farmers
# -------------------------

@app.get("/farmers")
def get_farmers():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM farmers")
    farmers = [dict(row) for row in cursor.fetchall()]

    connection.close()
    return farmers


# -------------------------
# Resources
# -------------------------

@app.get("/resources")
def get_resources():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM resources
        WHERE available = 1
        AND quantity > 0
    """)

    resources = [dict(row) for row in cursor.fetchall()]

    connection.close()
    return resources


# -------------------------
# Confirm booking
# -------------------------

@app.post("/bookings/confirm")
def confirm_booking(booking: BookingRequest):

    connection = get_db_connection()
    cursor = connection.cursor()

    # Check farmer
    cursor.execute(
        "SELECT * FROM farmers WHERE id = ?",
        (booking.farmer_id,)
    )

    farmer = cursor.fetchone()

    if not farmer:
        connection.close()
        raise HTTPException(status_code=404, detail="Farmer not found")

    # Check resource
    cursor.execute(
        "SELECT * FROM resources WHERE id = ?",
        (booking.resource_id,)
    )

    resource = cursor.fetchone()

    if not resource:
        connection.close()
        raise HTTPException(status_code=404, detail="Resource not found")

    # Check quantity
    if booking.quantity <= 0:
        connection.close()
        raise HTTPException(
            status_code=400,
            detail="Quantity must be greater than 0"
        )

    if resource["quantity"] < booking.quantity:
        connection.close()
        raise HTTPException(
            status_code=400,
            detail=f"Only {resource['quantity']} {resource['unit']} available"
        )

    # Check overlapping booking for machines/pumps
    if resource["resource_type"] in ["tractor", "pump", "solar_pump"]:

        cursor.execute("""
            SELECT id
            FROM bookings
            WHERE resource_id = ?
            AND booking_date = ?
            AND status = 'confirmed'
            AND start_time < ?
            AND end_time > ?
        """, (
            booking.resource_id,
            booking.booking_date,
            booking.end_time,
            booking.start_time
        ))

        conflict = cursor.fetchone()

        if conflict:
            connection.close()
            raise HTTPException(
                status_code=409,
                detail="Resource is already booked during this time"
            )

    # Calculate cost
    total_cost = 0

    if resource["price_per_hour"] and resource["price_per_hour"] > 0:
        start_hour = int(booking.start_time.split(":")[0])
        end_hour = int(booking.end_time.split(":")[0])

        hours = end_hour - start_hour

        if hours <= 0:
            connection.close()
            raise HTTPException(
                status_code=400,
                detail="Invalid booking time"
            )

        total_cost = hours * resource["price_per_hour"]

    elif resource["price_per_unit"] and resource["price_per_unit"] > 0:
        total_cost = booking.quantity * resource["price_per_unit"]

    # Create booking
    cursor.execute("""
        INSERT INTO bookings (
            farmer_id,
            resource_id,
            booking_date,
            start_time,
            end_time,
            quantity,
            total_cost,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 'confirmed')
    """, (
        booking.farmer_id,
        booking.resource_id,
        booking.booking_date,
        booking.start_time,
        booking.end_time,
        booking.quantity,
        total_cost
    ))

    booking_id = cursor.lastrowid

    # Reduce quantity only for input resources.
    # Machines and pumps are reserved by time, not consumed.

    if resource["resource_type"] in ["tractor", "pump", "solar_pump"]:
        new_quantity = resource["quantity"]
        new_available = 1
        new_status = "available"
    else:
        new_quantity = resource["quantity"] - booking.quantity
        new_available = 1 if new_quantity > 0 else 0
        new_status = "available" if new_quantity > 0 else "unavailable"

    cursor.execute("""
        UPDATE resources
        SET quantity = ?,
            available = ?,
            status = ?
        WHERE id = ?
    """, (
        new_quantity,
        new_available,
        new_status,
        booking.resource_id
    ))

    connection.commit()
    connection.close()

    return {
        "message": "Booking confirmed successfully",
        "booking_id": booking_id,
        "farmer_id": booking.farmer_id,
        "resource_id": booking.resource_id,
        "booking_date": booking.booking_date,
        "start_time": booking.start_time,
        "end_time": booking.end_time,
        "quantity_booked": booking.quantity,
        "remaining_quantity": new_quantity,
        "total_cost": total_cost,
        "status": "confirmed"
    }
# -------------------------
# Get bookings
# -------------------------

@app.get("/bookings")
def get_bookings():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            b.id,
            b.farmer_id,
            f.name AS farmer_name,
            b.resource_id,
            r.name AS resource_name,
            r.resource_type,
            b.booking_date,
            b.start_time,
            b.end_time,
            b.quantity,
            b.total_cost,
            b.status
        FROM bookings b
        JOIN farmers f ON b.farmer_id = f.id
        JOIN resources r ON b.resource_id = r.id
        ORDER BY b.id
    """)

    bookings = [dict(row) for row in cursor.fetchall()]

    connection.close()
    return bookings
