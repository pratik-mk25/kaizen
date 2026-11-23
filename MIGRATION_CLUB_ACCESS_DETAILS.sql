BEGIN;

-- Existing requests predate these fields. Preserve them for manual review.
ALTER TABLE public.club_access_requests
    ADD COLUMN college_name text CHECK (char_length(college_name) BETWEEN 1 AND 120 AND college_name = btrim(college_name) AND college_name !~ '[[:cntrl:]]'),
    ADD COLUMN applicant_name text CHECK (char_length(applicant_name) BETWEEN 1 AND 120 AND applicant_name = btrim(applicant_name) AND applicant_name !~ '[[:cntrl:]]'),
    ADD COLUMN designation text CHECK (char_length(designation) BETWEEN 1 AND 120 AND designation = btrim(designation) AND designation !~ '[[:cntrl:]]');

GRANT INSERT (college_name, applicant_name, designation)
    ON public.club_access_requests TO service_role;

COMMIT;
