-- Mission Tracker v2: Comprehensive Multi-Tenancy & Schema Bootstrap
-- This script is idempotent: it will create missing tables and add missing columns.

-- 0. Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Create Organizations Table
CREATE TABLE IF NOT EXISTS public.organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Ensure Core Tables Exist (v2 Schema)

-- Profiles
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID REFERENCES auth.users PRIMARY KEY,
    role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('member', 'lead', 'admin')),
    username TEXT UNIQUE,
    display_name TEXT,
    avatar_url TEXT,
    organization_id UUID REFERENCES organizations(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Missions
CREATE TABLE IF NOT EXISTS public.missions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    organization_id UUID REFERENCES organizations(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Projects
CREATE TABLE IF NOT EXISTS public.projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mission_id UUID REFERENCES missions(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    lead_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    organization_id UUID REFERENCES organizations(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tasks
CREATE TABLE IF NOT EXISTS public.tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo', 'in_progress', 'done')),
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    due_date DATE,
    organization_id UUID REFERENCES organizations(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Task Assignees (Junction Table)
CREATE TABLE IF NOT EXISTS public.task_assignees (
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    PRIMARY KEY (task_id, user_id)
);

-- Task Attachments
CREATE TABLE IF NOT EXISTS public.task_attachments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    uploader_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    file_name TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    mime_type TEXT,
    file_size INT,
    organization_id UUID REFERENCES organizations(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Comments
CREATE TABLE IF NOT EXISTS public.comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    user_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    content TEXT NOT NULL,
    organization_id UUID REFERENCES organizations(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audit Logs
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    old_values JSONB,
    new_values JSONB,
    organization_id UUID REFERENCES organizations(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Add organization_id to existing tables if they were already created without it
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='profiles' AND column_name='organization_id') THEN
        ALTER TABLE public.profiles ADD COLUMN organization_id UUID REFERENCES organizations(id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='missions' AND column_name='organization_id') THEN
        ALTER TABLE public.missions ADD COLUMN organization_id UUID REFERENCES organizations(id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='projects' AND column_name='organization_id') THEN
        ALTER TABLE public.projects ADD COLUMN organization_id UUID REFERENCES organizations(id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tasks' AND column_name='organization_id') THEN
        ALTER TABLE public.tasks ADD COLUMN organization_id UUID REFERENCES organizations(id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='comments' AND column_name='organization_id') THEN
        ALTER TABLE public.comments ADD COLUMN organization_id UUID REFERENCES organizations(id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='task_attachments' AND column_name='organization_id') THEN
        ALTER TABLE public.task_attachments ADD COLUMN organization_id UUID REFERENCES organizations(id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='audit_logs' AND column_name='organization_id') THEN
        ALTER TABLE public.audit_logs ADD COLUMN organization_id UUID REFERENCES organizations(id);
    END IF;
END $$;

-- 4. Setup Row Level Security (RLS)
ALTER TABLE public.missions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.task_attachments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

-- 5. Policies
-- These policies assume that the user's organization_id is stored in their profile.
CREATE POLICY "Missions are visible by organization members" ON public.missions
    FOR SELECT USING (organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid()));

CREATE POLICY "Projects are visible by organization members" ON public.projects
    FOR SELECT USING (organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid()));

CREATE POLICY "Tasks are visible by organization members" ON public.tasks
    FOR SELECT USING (organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid()));

-- Add more policies as needed for INSERT/UPDATE/DELETE
