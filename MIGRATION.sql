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
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='profiles' AND column_name='email') THEN
        ALTER TABLE public.profiles ADD COLUMN email TEXT;
    END IF;
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
-- These policies allow organization members to interact with their data based on their roles.

-- PROFILES
DROP POLICY IF EXISTS "Users can view their own profiles" ON public.profiles;
CREATE POLICY "Users can view their own profiles" ON public.profiles FOR SELECT USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update their own profiles" ON public.profiles;
CREATE POLICY "Users can update their own profiles" ON public.profiles FOR UPDATE USING (auth.uid() = id);

-- MISSIONS
DROP POLICY IF EXISTS "Missions are visible by organization members" ON public.missions;
CREATE POLICY "Missions are visible by organization members" ON public.missions FOR SELECT USING (organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid()));

DROP POLICY IF EXISTS "Admins can create missions" ON public.missions;
CREATE POLICY "Admins can create missions" ON public.missions FOR INSERT WITH CHECK (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'));

DROP POLICY IF EXISTS "Admins can update missions" ON public.missions;
CREATE POLICY "Admins can update missions" ON public.missions FOR UPDATE USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'));

DROP POLICY IF EXISTS "Admins can delete missions" ON public.missions;
CREATE POLICY "Admins can delete missions" ON public.missions FOR DELETE USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'));

-- PROJECTS
DROP POLICY IF EXISTS "Projects are visible by organization members" ON public.projects;
CREATE POLICY "Projects are visible by organization members" ON public.projects FOR SELECT USING (organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid()));

DROP POLICY IF EXISTS "Leads/Admins can manage projects" ON public.projects;
CREATE POLICY "Leads/Admins can manage projects" ON public.projects FOR ALL USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role IN ('admin', 'lead')));

-- TASKS
DROP POLICY IF EXISTS "Tasks are visible by organization members" ON public.tasks;
CREATE POLICY "Tasks are visible by organization members" ON public.tasks FOR SELECT USING (organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid()));

DROP POLICY IF EXISTS "Everyone in org can manage tasks" ON public.tasks;
CREATE POLICY "Everyone in org can manage tasks" ON public.tasks FOR ALL USING (organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid()));

-- AUDIT LOGS
DROP POLICY IF EXISTS "Users can insert audit logs" ON public.audit_logs;
CREATE POLICY "Users can insert audit logs" ON public.audit_logs FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can view org audit logs" ON public.audit_logs;
CREATE POLICY "Users can view org audit logs" ON public.audit_logs FOR SELECT USING (organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid()));

-- COMMENTS & ATTACHMENTS
DROP POLICY IF EXISTS "Org members can manage comments" ON public.comments;
CREATE POLICY "Org members can manage comments" ON public.comments FOR ALL USING (organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid()));

DROP POLICY IF EXISTS "Org members can manage attachments" ON public.task_attachments;
CREATE POLICY "Org members can manage attachments" ON public.task_attachments FOR ALL USING (organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid()));

-- ASSIGNEES
ALTER TABLE public.task_assignees ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Org members can manage assignees" ON public.task_assignees;
CREATE POLICY "Org members can manage assignees" ON public.task_assignees FOR ALL USING (EXISTS (
    SELECT 1 FROM tasks t JOIN profiles p ON t.organization_id = p.organization_id 
    WHERE t.id = task_id AND p.id = auth.uid()
));

-- 6. Trigger to sync profiles with auth.users
CREATE OR REPLACE FUNCTION public.handle_new_user() 
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, email, username)
  VALUES (new.id, new.email, 'vhng_' || substr(new.id::text, 1, 8));
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

-- 7. Helper Function for Non-Recursive Policy Checks
CREATE OR REPLACE FUNCTION public.is_admin() 
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.profiles 
    WHERE id = auth.uid() AND role = 'admin'
  );
$$ LANGUAGE sql SECURITY DEFINER;

-- 8. Additional Profiles Policies
DROP POLICY IF EXISTS "Admins can view all profiles in their org" ON public.profiles;
CREATE POLICY "Admins can view all profiles in their org" ON public.profiles 
FOR SELECT USING (public.is_admin());
