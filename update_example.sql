-- When a rescan shows improvement:
INSERT INTO platform_scans (
  submission_id, platform, risk_score, risk_level, 
  findings, scan_version, previous_scan_id, improvement_score
) VALUES (
  'submission-uuid', 'youtube', 25.5, 'low',
  '{"issues_fixed": ["copyright_music"]}'::jsonb,
  2, 
  (SELECT id FROM platform_scans WHERE submission_id = 'submission-uuid' AND scan_version = 1),
  60.5  -- 85.5 - 25.5 = 60% improvement!
);
