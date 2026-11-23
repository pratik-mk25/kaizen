BEGIN;

CREATE TABLE public.club_access_requests (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    club_name text NOT NULL CHECK (
        char_length(club_name) BETWEEN 1 AND 120 AND club_name = btrim(club_name)
        AND club_name !~ '[[:cntrl:]]'
    ),
    contact_email text NOT NULL CHECK (
        contact_email = lower(contact_email) AND char_length(contact_email) <= 254
        AND char_length(split_part(contact_email, '@', 1)) BETWEEN 1 AND 64
        AND contact_email ~ '^[^[:space:]@]+@[^[:space:]@.]+(\.[^[:space:]@.]+)+$'
    ),
    status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'declined')),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX club_access_requests_pending_contact
    ON public.club_access_requests (lower(club_name), contact_email)
    WHERE status = 'pending';

-- No client policies: anonymous and signed-in clients have no row access.
ALTER TABLE public.club_access_requests ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.club_access_requests FROM PUBLIC, anon, authenticated, service_role;
GRANT INSERT (club_name, contact_email) ON public.club_access_requests TO service_role;

COMMIT;
