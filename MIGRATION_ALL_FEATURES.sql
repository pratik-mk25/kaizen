-- ====================================================
-- KAIZEN: Migration for Flight Logbook, Batteries, Checkouts & Events
-- ====================================================

-- 1. Flight Logs Table
CREATE TABLE IF NOT EXISTS flight_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pilot_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    equipment_id UUID REFERENCES equipment(id) ON DELETE SET NULL,
    battery_id UUID,
    flight_date TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL DEFAULT 0,
    location TEXT,
    purpose TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Battery Packs Table
CREATE TABLE IF NOT EXISTS battery_packs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    cell_count TEXT DEFAULT '4S',
    capacity_mah INTEGER DEFAULT 1500,
    charge_cycles INTEGER DEFAULT 0,
    status TEXT DEFAULT 'healthy',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Equipment Checkouts Table
CREATE TABLE IF NOT EXISTS equipment_checkouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    equipment_id UUID REFERENCES equipment(id) ON DELETE CASCADE,
    borrower_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    checked_out_at TIMESTAMPTZ DEFAULT NOW(),
    expected_return_at TEXT,
    returned_at TIMESTAMPTZ,
    condition_on_checkout TEXT DEFAULT 'good',
    condition_on_return TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Events Table
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    event_type TEXT DEFAULT 'workshop',
    event_date TEXT NOT NULL,
    location TEXT,
    created_by UUID REFERENCES profiles(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Event Attendees Table
CREATE TABLE IF NOT EXISTS event_attendees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'registered',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
