# 📑 Complete Project Specification & Viva Documentation
## Project: Dhanush OmniTransit & Logistics (DOTL)
### Multi-Modal Synchronized Passenger Transit & Freight Hitching Platform

---

## 1. Abstract & Motivation

Urbanization and inter-city commerce across developing nations like India have led to congested highway networks and high fuel emissions. Simultaneously, transport operations remain deeply fragmented:
1. **Passenger Transport Systems (State & Private Buses)** operate thousands of daily trips on strict timetables, carrying passengers with luggage compartments that are 40% to 70% under-utilized on average.
2. **Freight & Express Courier Logistics** operate independent vans, small commercial vehicles (SCVs), and heavy trucks, often running empty return journeys (deadheading) and incurring excessive logistics costs.

**Dhanush OmniTransit** introduces the **Cargo-Hitching Dual-Transit Model**, an optimization framework where passenger vehicles double as rapid freight carriers. By using spare luggage bays on intercity passenger coaches, small-to-medium parcels reach destinations on the exact same schedule as travelers, slashing delivery turnaround from days to hours, lowering transport costs by 25-40%, and substantially cutting carbon emissions.

---

## 2. Mathematical Formulation & Allocation Algorithm

### 2.1 The Dual-Capacity Constraint
For any vehicle $v$ operating on trip $t$ along route $r$:
- Let $S_v$ be total passenger seats.
- Let $W_v$ be total cargo weight capacity (kg).
- Let $V_v$ be total cargo volumetric capacity ($\text{m}^3$).
- Let $s_t$ be currently reserved passenger seats.
- Let $w_t$ be currently loaded cargo weight.
- Let $v_t$ be currently occupied cargo volume.

The vehicle operational constraints are:
$$s_t \le S_v$$
$$w_t = \sum_{i \in C_t} \text{weight}(i) \le W_v$$
$$v_t = \sum_{i \in C_t} \text{volume}(i) \le V_v$$

Where $C_t$ is the set of consignments hitched onto trip $t$.

### 2.2 Cargo-Hitch Decision Rule
When a cargo booking request arrives with weight $w_{req}$, volume $v_{req}$, origin $O$, and destination $D$:

```text
Algorithm: Smart Dual-Transit Dispatcher
Input: Consignment C(w, v, O, D), ScheduledTrips T
Output: TransportMode M, AssignedTrip T_assign

1. IF w > 150 kg OR PreferredMode == 'Dedicated Heavy Freight':
       Assign to Dedicated Heavy Freight Fleet
       Return (Dedicated Freight, NextAvailableFreightTrip)

2. Find candidate passenger trips:
       Candidates = { t in T | route(t).origin == O 
                               AND route(t).destination == D 
                               AND status(t) in ('Scheduled', 'Boarding', 'In Transit')
                               AND (W_v - w_t) >= w
                               AND (V_v - v_t) >= v }

3. IF Candidates is not empty:
       Select trip t* with earliest departure / closest ETA
       Reserve w and v in trip t*
       Return (Cargo-Hitch on Passenger Bus, t*)
   ELSE:
       Assign to Dedicated Logistics Fleet / Next Available Batch
       Return (Dedicated Freight, NextAvailableTrip)
```

---

## 3. Database Entity-Relationship (ER) Schema

```text
+------------------+         +--------------------+         +-------------------+
|      HUBS        | 1     * |       ROUTES       | 1     * |       TRIPS       |
+------------------+---------+--------------------+---------+-------------------+
| id (PK)          | origin  | id (PK)            | route_id| id (PK)           |
| code (UNIQUE)    | dest    | route_code         |         | trip_code (UNIQUE)|
| name             |         | origin_hub_id (FK) |         | route_id (FK)     |
| city             |         | dest_hub_id (FK)   |         | vehicle_id (FK)   |
| state            |         | distance_km        |         | departure_time    |
| lat, lng         |         | duration_hours     |         | arrival_time      |
| phone            |         | base_passenger_fare|         | current_lat, lng  |
+------------------+         | base_cargo_rate_kg |         | progress_pct      |
                             +--------------------+         | booked_seats      |
                                                            | booked_cargo_kg   |
+------------------+                                        +-------------------+
|    VEHICLES      | 1                                                | 1
+------------------+                                                |
| id (PK)          |                                                |
| reg_number (UQ)  |                                                |
| name             |                                                |
| vehicle_type     |                                                |
| total_seats      |                                                |
| total_cargo_kg   |                                                |
| driver_name/phone|                                                |
+------------------+                                                |
         | 1                                                        |
         |                                          +---------------+---------------+
         | *                                        | *                             | *
+--------------------+                     +--------------------+         +----------------------+
|       TRIPS        |                     | PASSENGER_BOOKINGS |         |  CARGO_CONSIGNMENTS  |
+--------------------+                     +--------------------+         +----------------------+
                                           | id (PK)            |         | id (PK)              |
                                           | pnr (UNIQUE)       |         | awb (UNIQUE)         |
                                           | trip_id (FK)       |         | trip_id (FK)         |
                                           | passenger_name     |         | origin_hub_id (FK)   |
                                           | passenger_phone    |         | dest_hub_id (FK)     |
                                           | seat_number        |         | sender_name/phone    |
                                           | fare_amount        |         | receiver_name/phone  |
                                           | status             |         | weight_kg, volume    |
                                           | qr_code            |         | transport_mode       |
                                           +--------------------+         | price_amount, status |
                                                                          +----------------------+
```

---

## 4. Key Questions & Viva / Technical Defense

### Q1: What is the fundamental innovation in this project compared to conventional bus booking or parcel tracking apps?
**Answer:** Conventional systems operate in silos: RedBus only handles passenger seats; FedEx/BlueDart only handles freight vehicles. **Dhanush OmniTransit** implements **Cargo-Hitching**, an algorithmically synchronized dual-transit model where passenger buses utilize spare luggage hold capacity to transport express freight along pre-scheduled routes, saving capital costs, reducing delivery time to same-day, and lowering highway carbon emissions.

### Q2: How does the system ensure safety between passengers and cargo?
**Answer:** 
1. **Weight & Dimension Caps:** Packages above 150 kg or oversized items are strictly routed to dedicated freight trucks to avoid overburdening passenger coaches.
2. **Category Isolation:** Hazardous materials or inflammable items are barred; only validated categories (e-commerce parcels, electronics, medicines, documents) are hitched.
3. **Physical Partitioning:** Hitching occurs in lower, climate-controlled, sealed undercarriage compartments, entirely separate from passenger seating cabins.

### Q3: How is real-time telematics simulated and tracked?
**Answer:** Vehicles update their geographic coordinates along the pre-computed route polyline. Both passenger tickets (PNRs) and cargo consignment waybills (AWBs) link to the exact same trip vehicle. Calling `/fleet/simulate-step/<id>` computes intermediate interpolation coordinates between origin and destination coordinates, updating the live Leaflet map and appending milestone logs.

### Q4: How is CO₂ savings calculated?
**Answer:** The average light commercial vehicle (LCV) emits approximately $0.18 \text{ kg CO}_2$ per ton-kilometer. By utilizing pre-existing passenger bus runs to move freight rather than dispatching a separate delivery van:
$$\text{CO}_2 \text{ Saved (kg)} = \left(\frac{\text{Hitched Cargo (kg)}}{1000}\right) \times \text{Distance (km)} \times 0.18$$

---

## 5. Technology Stack Summary

- **Backend Framework**: Python 3.13, Flask 3.1.3
- **Database**: SQLite3 with Foreign Key Cascades & Row Factories
- **Templating**: Jinja2 with custom filters
- **Frontend & Styling**: Tailwind CSS via CDN, JetBrains Mono & Plus Jakarta Sans typography
- **Interactive Maps & Telematics**: Leaflet.js 1.9.4 with OpenStreetMap raster tiles
- **Icons**: FontAwesome 6 Pro CDN
- **Automated Testing**: Python `unittest` test suite
