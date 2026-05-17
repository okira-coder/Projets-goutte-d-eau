-- Stations SYNOP Occitanie pour le MVP
USE goutte_eau;

INSERT INTO stations (synop_code, name, department, latitude, longitude, altitude_m, region) VALUES
  ('07643', 'Montpellier-Fréjorgues', 'Hérault',             43.576944, 3.963056,   2, 'Occitanie'),
  ('07630', 'Toulouse-Blagnac',       'Haute-Garonne',       43.621389, 1.378889, 151, 'Occitanie'),
  ('07747', 'Perpignan-Rivesaltes',   'Pyrénées-Orientales', 42.737222, 2.872500,  42, 'Occitanie'),
  ('07621', 'Carcassonne-Salvaza',    'Aude',                43.215000, 2.306400, 126, 'Occitanie');
