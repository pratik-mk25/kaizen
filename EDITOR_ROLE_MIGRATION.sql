-- Editor Role and Permissions Update

-- 1. Update the role check constraint (already updated in MIGRATION.sql, but here for the live database)
-- Note: You might need to drop the old constraint first if it has a specific name, 
-- but usually, re-applying the table definition is safer.

-- 2. Update Policies to allow 'editor' to see and manage everything

-- PROFILES
DROP POLICY IF EXISTS "Users can view their own profiles" ON public.profiles;
CREATE POLICY "Users can view their own profiles" ON public.profiles FOR SELECT USING (auth.uid() = id OR (SELECT role FROM profiles WHERE id = auth.uid()) = 'editor');

DROP POLICY IF EXISTS "Users can update their own profiles" ON public.profiles;
CREATE POLICY "Users can update their own profiles" ON public.profiles FOR UPDATE USING (auth.uid() = id OR (SELECT role FROM profiles WHERE id = auth.uid()) = 'editor');

DROP POLICY IF EXISTS "Users can insert their own profiles" ON public.profiles;
CREATE POLICY "Users can insert their own profiles" ON public.profiles FOR INSERT WITH CHECK (auth.uid() = id OR (SELECT role FROM profiles WHERE id = auth.uid()) = 'editor');

-- MISSIONS
DROP POLICY IF EXISTS "Missions are visible by organization members" ON public.missions;
CREATE POLICY "Missions are visible by organization members" ON public.missions FOR SELECT USING (organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid()) OR (SELECT role FROM profiles WHERE id = auth.uid()) = 'editor');

DROP POLICY IF EXISTS "Admins can create missions" ON public.missions;
CREATE POLICY "Admins can create missions" ON public.missions FOR INSERT WITH CHECK (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role IN ('admin', 'editor')));

DROP POLICY IF EXISTS "Admins can update missions" ON public.missions;
CREATE POLICY "Admins can update missions" ON public.missions FOR UPDATE USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role IN ('admin', 'editor')));

DROP POLICY IF EXISTS "Admins can delete missions" ON public.missions;
CREATE POLICY "Admins can delete missions" ON public.missions FOR DELETE USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role IN ('admin', 'editor')));

-- PROJECTS
DROP POLICY IF EXISTS "Projects are visible by organization members" ON public.projects;
CREATE POLICY "Projects are visible by organization members" ON public.projects FOR SELECT USING (organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid()) OR (SELECT role FROM profiles WHERE id = auth.uid()) = 'editor');

DROP POLICY IF EXISTS "Leads/Admins can manage projects" ON public.projects;
CREATE POLICY "Leads/Admins can manage projects" ON public.projects FOR ALL USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role IN ('admin', 'lead', 'editor')));

-- TASKS
DROP POLICY IF EXISTS "Tasks are visible by organization members" ON public.tasks;
CREATE POLICY "Tasks are visible by organization members" ON public.tasks FOR SELECT USING (organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid()) OR (SELECT role FROM profiles WHERE id = auth.uid()) = 'editor');

DROP POLICY IF EXISTS "Everyone in org can manage tasks" ON public.tasks;
CREATE POLICY "Everyone in org can manage tasks" ON public.tasks FOR ALL USING (organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid()) OR (SELECT role FROM profiles WHERE id = auth.uid()) = 'editor');

-- AUDIT LOGS
DROP POLICY IF EXISTS "Users can view org audit logs" ON public.audit_logs;
CREATE POLICY "Users can view org audit logs" ON public.audit_logs FOR SELECT USING (organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid()) OR (SELECT role FROM profiles WHERE id = auth.uid()) = 'editor');

-- Helper to set a user as editor
-- UPDATE public.profiles SET role = 'editor' WHERE email = 'your-email@example.com';
