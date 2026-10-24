import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'dhanush_transport.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Hubs / Terminals
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS hubs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        city TEXT NOT NULL,
        state TEXT NOT NULL,
        address TEXT NOT NULL,
        lat REAL NOT NULL,
        lng REAL NOT NULL,
        phone TEXT
    )
    ''')

    # 2. Vehicles (Hybrid Bus, Express Minivan, Dedicated Freight Truck)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS vehicles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reg_number TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        vehicle_type TEXT NOT NULL, -- 'Hybrid Passenger Bus', 'Express Cargo Minivan', 'Heavy Freight Truck'
        total_seats INTEGER DEFAULT 0,
        total_cargo_kg REAL DEFAULT 0,
        total_cargo_cbm REAL DEFAULT 0,
        driver_name TEXT NOT NULL,
        driver_phone TEXT NOT NULL,
        current_hub_id INTEGER,
        status TEXT DEFAULT 'Available', -- 'Available', 'In Transit', 'Maintenance'
        FOREIGN KEY (current_hub_id) REFERENCES hubs(id)
    )
    ''')

    # 3. Routes
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS routes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        route_code TEXT UNIQUE NOT NULL,
        origin_hub_id INTEGER NOT NULL,
        dest_hub_id INTEGER NOT NULL,
        distance_km REAL NOT NULL,
        duration_hours REAL NOT NULL,
        base_passenger_fare REAL NOT NULL,
        base_cargo_rate_kg REAL NOT NULL,
        FOREIGN KEY (origin_hub_id) REFERENCES hubs(id),
        FOREIGN KEY (dest_hub_id) REFERENCES hubs(id)
    )
    ''')

    # 4. Scheduled Trips (Unified trips carrying both passengers and hitching cargo)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trip_code TEXT UNIQUE NOT NULL,
        route_id INTEGER NOT NULL,
        vehicle_id INTEGER NOT NULL,
        departure_time TEXT NOT NULL,
        arrival_time TEXT NOT NULL,
        status TEXT DEFAULT 'Scheduled', -- 'Scheduled', 'Boarding & Loading', 'In Transit', 'Completed'
        current_lat REAL,
        current_lng REAL,
        progress_pct INTEGER DEFAULT 0,
        booked_seats INTEGER DEFAULT 0,
        booked_cargo_kg REAL DEFAULT 0,
        FOREIGN KEY (route_id) REFERENCES routes(id),
        FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
    )
    ''')

    # 5. Passenger Bookings
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS passenger_bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pnr TEXT UNIQUE NOT NULL,
        trip_id INTEGER NOT NULL,
        passenger_name TEXT NOT NULL,
        passenger_phone TEXT NOT NULL,
        passenger_email TEXT,
        seat_number TEXT NOT NULL,
        fare_amount REAL NOT NULL,
        status TEXT DEFAULT 'Confirmed', -- 'Confirmed', 'Boarded', 'Completed', 'Cancelled'
        booked_at TEXT NOT NULL,
        qr_code TEXT,
        FOREIGN KEY (trip_id) REFERENCES trips(id)
    )
    ''')

    # 6. Cargo Consignments
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cargo_consignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        awb TEXT UNIQUE NOT NULL,
        trip_id INTEGER,
        origin_hub_id INTEGER NOT NULL,
        dest_hub_id INTEGER NOT NULL,
        sender_name TEXT NOT NULL,
        sender_phone TEXT NOT NULL,
        sender_address TEXT,
        receiver_name TEXT NOT NULL,
        receiver_phone TEXT NOT NULL,
        receiver_address TEXT NOT NULL,
        weight_kg REAL NOT NULL,
        volume_cbm REAL DEFAULT 0.05,
        cargo_type TEXT NOT NULL, -- 'Documents', 'Electronics', 'Perishable / Fresh', 'E-Commerce Parcel', 'Heavy Commercial'
        transport_mode TEXT NOT NULL, -- 'Cargo-Hitch (Express via Passenger Fleet)', 'Dedicated Heavy Freight'
        price_amount REAL NOT NULL,
        status TEXT DEFAULT 'Booked', -- 'Booked', 'Loaded', 'In Transit', 'Arrived at Hub', 'Out for Delivery', 'Delivered'
        created_at TEXT NOT NULL,
        FOREIGN KEY (trip_id) REFERENCES trips(id),
        FOREIGN KEY (origin_hub_id) REFERENCES hubs(id),
        FOREIGN KEY (dest_hub_id) REFERENCES hubs(id)
    )
    ''')

    # 7. Tracking Milestones
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tracking_checkpoints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tracking_ref TEXT NOT NULL, -- PNR or AWB
        ref_type TEXT NOT NULL,    -- 'PASSENGER' or 'CARGO'
        stage_name TEXT NOT NULL,
        location TEXT NOT NULL,
        status_timestamp TEXT NOT NULL,
        notes TEXT,
        is_completed INTEGER DEFAULT 0
    )
    ''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully at:", DB_PATH)
