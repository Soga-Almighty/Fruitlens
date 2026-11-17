-- =====================================================================================
-- Fruit Lens: database setup for InsForge
--
-- HOW TO USE:  InsForge dashboard > SQL Editor > paste this whole file > Run.
-- It is safe to run again at any time: it never deletes or overwrites your scans or your edits.
--
-- What it creates
--   scans       one row per scan. Row Level Security makes every user see ONLY their own rows.
--   fruits, conditions, tips
--               the fruit guides shown in the app (you can edit them in Database > Tables).
--   scan_stats  a small function that counts the logged-in user's scans for the dashboard.
-- =====================================================================================

-- 1) Fruit guide content --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.fruits (
  slug           text PRIMARY KEY,
  name           text NOT NULL,
  scientific     text,
  category       text,
  description    text,
  image_url      text,
  ripen_duration text,
  storage_temp   text,
  storage_place  text,
  ethylene       text
);

CREATE TABLE IF NOT EXISTS public.conditions (
  fruit           text NOT NULL REFERENCES public.fruits(slug) ON DELETE CASCADE,
  condition       text NOT NULL,
  freshness_label text,
  base_freshness  integer NOT NULL,
  stage           integer NOT NULL,
  ripen_time      text,
  spoil_time      text,
  storage         text,
  consume         text,
  culinary        text,
  PRIMARY KEY (fruit, condition)
);

CREATE TABLE IF NOT EXISTS public.tips (
  id       integer PRIMARY KEY,
  title    text NOT NULL,
  body     text NOT NULL,
  priority text,
  icon     text
);

-- 2) Scans ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.scans (
  id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id       uuid NOT NULL DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE,
  fruit         text NOT NULL,
  label         text,
  condition     text,
  confidence    double precision,
  freshness     integer,
  stage         integer,
  probabilities jsonb,
  image_file    text,
  created_at    timestamptz NOT NULL DEFAULT now(),
  legacy_id     bigint
);

CREATE INDEX IF NOT EXISTS scans_user_created_idx ON public.scans (user_id, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS scans_user_legacy_idx ON public.scans (user_id, legacy_id) WHERE legacy_id IS NOT NULL;

-- 3) Security: Row Level Security (RLS) ----------------------------------------------
-- New tables are open to everybody until RLS is switched on, so this part is NOT optional.
ALTER TABLE public.scans      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fruits     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conditions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tips       ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.scans, public.fruits, public.conditions, public.tips FROM anon;

DROP POLICY IF EXISTS "scans: own rows only" ON public.scans;
CREATE POLICY "scans: own rows only" ON public.scans
  FOR ALL TO authenticated
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "fruits: signed-in users can read" ON public.fruits;
CREATE POLICY "fruits: signed-in users can read" ON public.fruits FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "conditions: signed-in users can read" ON public.conditions;
CREATE POLICY "conditions: signed-in users can read" ON public.conditions FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "tips: signed-in users can read" ON public.tips;
CREATE POLICY "tips: signed-in users can read" ON public.tips FOR SELECT TO authenticated USING (true);

-- 4) Dashboard numbers ---------------------------------------------------------------
-- Runs with the caller's rights, so RLS still applies: it only ever counts the caller's own scans.
CREATE OR REPLACE FUNCTION public.scan_stats()
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY INVOKER
AS $$
  SELECT jsonb_build_object(
    'total',         (SELECT count(*) FROM public.scans),
    'avg_freshness', (SELECT round(avg(freshness)) FROM public.scans),
    'this_week',     (SELECT count(*) FROM public.scans WHERE created_at >= now() - interval '7 days'),
    'last_week',     (SELECT count(*) FROM public.scans
                      WHERE created_at >= now() - interval '14 days' AND created_at < now() - interval '7 days'),
    'by_condition',  COALESCE((SELECT jsonb_object_agg(condition, n)
                               FROM (SELECT condition, count(*) AS n FROM public.scans GROUP BY condition) c), '{}'::jsonb),
    'by_fruit',      COALESCE((SELECT jsonb_object_agg(fruit, n)
                               FROM (SELECT fruit, count(*) AS n FROM public.scans GROUP BY fruit) f), '{}'::jsonb),
    'by_fruit_condition', COALESCE((SELECT jsonb_object_agg(fruit, conds)
                               FROM (SELECT fruit, jsonb_object_agg(condition, n) AS conds
                                     FROM (SELECT fruit, condition, count(*) AS n FROM public.scans GROUP BY fruit, condition) t
                                     GROUP BY fruit) u), '{}'::jsonb)
  );
$$;

-- 5) Starting content (existing rows are left untouched, so your edits survive a re-run) --
INSERT INTO public.fruits (slug, name, scientific, category, description, image_url, ripen_duration, storage_temp, storage_place, ethylene) VALUES
  ('banana', 'Banana', 'Musa acuminata', 'Tropical', 'High-potassium climacteric fruit. The peel shifts from green to yellow, then brown-spotted as starch turns to sugar.', 'https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?auto=format&fit=crop&q=80&w=400', '3-7 days', '13°C - 15°C', 'Cool room, away from direct sun', 'High ethylene producer'),
  ('tomato', 'Tomato', 'Solanum lycopersicum', 'Fruit vegetable', 'Rich in lycopene. Colour moves from green to deep red while the flesh softens; cold storage dulls flavour.', 'https://images.unsplash.com/photo-1592924357228-91a4daadcfea?auto=format&fit=crop&q=80&w=400', '2-5 days', '13°C - 18°C', 'Counter, stem-side down', 'Moderate ethylene producer'),
  ('papaya', 'Papaya', 'Carica papaya', 'Tropical', 'Tropical fruit with papain enzyme. Skin turns from green to yellow-orange and the flesh softens as it ripens.', 'https://images.unsplash.com/photo-1617112848923-cc2234396a8d?auto=format&fit=crop&q=80&w=400', '4-8 days', '20°C - 24°C (10°C - 13°C once ripe)', 'Room temperature, fridge once ripe', 'High ethylene producer'),
  ('rambutan', 'Rambutan', 'Nephelium lappaceum', 'Tropical', 'Hairy-shelled fruit that does not ripen after harvest. Spines turn from yellow-green to red; the skin browns fast.', 'https://images.unsplash.com/photo-1635830092719-0e3b5aedc364?auto=format&fit=crop&q=80&w=800', 'Does not ripen after harvest', '10°C - 12°C', 'Fridge, perforated bag', 'Low ethylene producer'),
  ('orange', 'Orange', 'Citrus × sinensis', 'Citrus', 'Citrus rich in Vitamin C. Non-climacteric, so it will not sweeten after picking; a firm rind with even colour is best.', 'https://images.unsplash.com/photo-1611080626919-7cf5a9dbab5b?auto=format&fit=crop&q=80&w=400', 'Does not ripen after harvest', '4°C - 8°C', 'Cool ventilated area or fridge crisper', 'Very low ethylene producer')
ON CONFLICT (slug) DO NOTHING;

INSERT INTO public.conditions (fruit, condition, freshness_label, base_freshness, stage, ripen_time, spoil_time, storage, consume, culinary) VALUES
  ('banana', 'Unripe', 'Green & starchy', 65, 1, '3-6 Days', '8-12 Days', 'Keep at room temperature. A paper bag or a ripe fruit nearby speeds ripening.', 'Wait until yellow with a few spots; green bananas are starchy.', 'Green bananas can be boiled or fried as a savoury side or chips.'),
  ('banana', 'Ripe', 'Optimal peak freshness', 90, 2, '0 Days', '3-5 Days', 'Keep away from other ethylene-sensitive produce. Wrap the crown in foil to slow ripening.', 'Best eaten within 2-3 days for the ideal sugar and texture balance.', 'Great for snacking, smoothies, oatmeal or fried banana.'),
  ('banana', 'Rotten', 'Decomposed surface', 10, 4, 'Expired', '0 Days', 'Isolate immediately so mould spores do not spread to nearby fruit.', 'Do not eat. Discard if you see mould, slime, leaking juice or a fermented smell.', 'Not suitable for cooking. Send to compost or organic waste.'),
  ('tomato', 'Unripe', 'Green & firm', 65, 1, '3-7 Days', '10-14 Days', 'Ripen at room temperature out of direct sun. Do not refrigerate: cold blocks ripening.', 'Wait until fully red and slightly soft for the best flavour.', 'Green tomatoes can be fried, pickled or made into green sambal.'),
  ('tomato', 'Ripe', 'Peak firm ripeness', 90, 2, '0 Days', '3-5 Days', 'Store stem-side down on the counter. Chill only to extend life, then warm up before eating.', 'Eat within 3-4 days, raw for the best flavour.', 'Ideal for salads, sandwiches, fresh sauces and sambal.'),
  ('tomato', 'Rotten', 'Decomposed surface', 10, 4, 'Expired', '0 Days', 'Isolate immediately so mould spores do not spread to nearby fruit.', 'Do not eat. Discard if you see mould, slime, leaking juice or a fermented smell.', 'Not suitable for cooking. Send to compost or organic waste.'),
  ('papaya', 'Unripe', 'Maturing phase', 65, 1, '3-5 Days', '8-10 Days', 'Keep at room temperature until about 70% of the skin is yellow. Avoid the fridge while green.', 'Wait for yellow-orange skin and a slight give before cutting for sweet flesh.', 'Green papaya works in savoury dishes such as urap, vegetable soup or som tum.'),
  ('papaya', 'Ripe', 'Optimal peak freshness', 90, 2, '0 Days', '2-4 Days', 'Move to the fridge to slow ripening and keep the flesh firm.', 'Eat within 2-3 days; ripe papaya bruises easily.', 'Fresh slices, fruit salad, smoothies or iced fruit desserts.'),
  ('papaya', 'Rotten', 'Decomposed surface', 10, 4, 'Expired', '0 Days', 'Isolate immediately so mould spores do not spread to nearby fruit.', 'Do not eat. Discard if you see mould, slime, leaking juice or a fermented smell.', 'Not suitable for cooking. Send to compost or organic waste.'),
  ('rambutan', 'Unripe', 'Immature (yellow-green)', 65, 1, 'Won''t ripen further', '3-5 Days', 'Rambutan does not ripen after picking. Keep cool in a perforated bag.', 'Likely sour or astringent; choose fully red fruit when possible.', 'Add to fruit salad or syrup to balance the sourness.'),
  ('rambutan', 'Ripe', 'Peak freshness', 90, 2, '0 Days', '3-5 Days', 'Refrigerate in a perforated bag; the skin browns quickly at room temperature.', 'Eat within 2-3 days while the flesh is at its sweetest.', 'Eat fresh, serve chilled, or add to mixed fruit desserts.'),
  ('rambutan', 'Rotten', 'Decomposed surface', 10, 4, 'Expired', '0 Days', 'Isolate immediately so mould spores do not spread to nearby fruit.', 'Do not eat. Discard if you see mould, slime, leaking juice or a fermented smell.', 'Not suitable for cooking. Send to compost or organic waste.'),
  ('orange', 'Unripe', 'Immature rind', 65, 1, 'Won''t ripen further', '1-2 Weeks', 'Oranges do not ripen after picking. Keep in a cool, ventilated place.', 'May taste sour. Rind colour alone is not a reliable maturity sign for every variety.', 'Juice with a little honey, or use zest and slices in marinades.'),
  ('orange', 'Ripe', 'Optimal peak freshness', 90, 2, '0 Days', '1-2 Weeks', 'Keep in a cool ventilated place or the fridge crisper. Keep dry to avoid mould.', 'Eat or juice within 1-2 weeks for the best juiciness and Vitamin C.', 'Fresh segments, juice, dressings, or zest in baking.'),
  ('orange', 'Rotten', 'Decomposed surface', 10, 4, 'Expired', '0 Days', 'Isolate immediately so mould spores do not spread to nearby fruit.', 'Do not eat. Discard if you see mould, slime, leaking juice or a fermented smell.', 'Not suitable for cooking. Send to compost or organic waste.')
ON CONFLICT (fruit, condition) DO NOTHING;

INSERT INTO public.tips (id, title, body, priority, icon) VALUES
  (1, 'Ethylene Gas Separation', 'Bananas, tomatoes and papayas release ethylene, which speeds up ripening of nearby produce. Store them apart from fruit you want to keep longer, such as oranges.', 'High Priority', 'split'),
  (2, 'Refrigeration Timing', 'Do not refrigerate tomatoes or papayas while they are still green: chilling interrupts ripening. Once ripe, the fridge helps papaya and rambutan last longer.', 'Pro Tip', 'refrigerator'),
  (3, 'Check Fruit Daily', 'Inspect stored fruit every day. One rotting fruit can spread mould to the rest of the bowl.', 'Habit', 'calendar-check'),
  (4, 'Wash Just Before Eating', 'Moisture speeds up mould growth. Keep fruit dry in storage and rinse it right before eating.', 'Pro Tip', 'droplets')
ON CONFLICT (id) DO NOTHING;

-- 6) Tell the API that the tables changed
NOTIFY pgrst, 'reload schema';
