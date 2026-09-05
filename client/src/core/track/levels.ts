import type { LevelDefinition } from '@shared/trackTypes';

export const LEVELS: LevelDefinition[] = [
  { id: 1, name: 'Premiers Tours', environment: 'neon_city', bronzeMs: 21000, silverMs: 17000, goldMs: 14000,
    pattern: ['ramp_small', 'gap_small', 'platform_wide', 'small_bump', 'flat_recovery', 'ramp_small', 'gap_small', 'platform_wide'] },
  { id: 2, name: 'Vagues de Néon', environment: 'neon_city', bronzeMs: 23000, silverMs: 18500, goldMs: 15000,
    pattern: ['long_climb', 'long_descent', 'ramp_small', 'gap_small', 'platform_wide', 'roller', 'flat_recovery'] },
  { id: 3, name: 'Dunes Chaudes', environment: 'desert', bronzeMs: 23500, silverMs: 19000, goldMs: 15500,
    pattern: ['ramp_medium', 'gap_medium', 'platform_wide', 'small_bump', 'ramp_small', 'gap_small', 'plateau'] },
  { id: 4, name: 'Crêtes de Sable', environment: 'desert', bronzeMs: 22000, silverMs: 17500, goldMs: 14000,
    pattern: ['platform_inclined', 'ramp_medium', 'gap_medium', 'roller', 'barrier_low', 'flat_recovery'] },
  { id: 5, name: 'Oasis Perdue', environment: 'desert', bronzeMs: 25500, silverMs: 20500, goldMs: 16500,
    pattern: ['tunnel', 'gap_medium', 'ramp_medium', 'platform_wide', 'big_roller', 'gap_small', 'platform_wide'] },

  { id: 6, name: 'Zone Industrielle', environment: 'industrial', bronzeMs: 26000, silverMs: 21000, goldMs: 17000,
    pattern: ['ramp_large', 'gap_large', 'platform_narrow', 'wall_vertical', 'flat_recovery', 'ramp_medium', 'gap_medium'] },
  { id: 7, name: 'Chaîne de Montage', environment: 'industrial', bronzeMs: 25000, silverMs: 20000, goldMs: 16000,
    pattern: ['tunnel_narrow', 'gap_medium', 'platform_moving_h', 'ramp_medium', 'gap_large', 'platform_wide'] },
  { id: 8, name: 'Acier et Rouille', environment: 'industrial', bronzeMs: 25500, silverMs: 20500, goldMs: 16500,
    pattern: ['barrier_series', 'ramp_large', 'gap_large', 'platform_narrow', 'roller', 'gap_medium'] },
  { id: 9, name: 'Pont Suspendu', environment: 'sky', bronzeMs: 27000, silverMs: 21500, goldMs: 17000,
    pattern: ['platform_falling', 'gap_medium', 'ramp_large', 'platform_rotating', 'gap_large', 'flat_recovery'] },
  { id: 10, name: 'Portes du Ciel', environment: 'sky', bronzeMs: 27500, silverMs: 22000, goldMs: 17500,
    pattern: ['demi_loop', 'gap_medium', 'ramp_large', 'gap_large', 'platform_narrow', 'tunnel'] },

  { id: 11, name: 'Cratère Brûlant', environment: 'volcano', bronzeMs: 30000, silverMs: 24000, goldMs: 19000,
    pattern: ['loop', 'gap_large', 'platform_narrow', 'wall_inclined', 'ramp_large', 'gap_huge'] },
  { id: 12, name: 'Coulée de Lave', environment: 'volcano', bronzeMs: 28500, silverMs: 22500, goldMs: 17500,
    pattern: ['flip_gap_single', 'platform_narrow', 'tunnel_low_ceiling', 'gap_large', 'ramp_large'] },
  { id: 13, name: 'Faille Ardente', environment: 'volcano', bronzeMs: 31500, silverMs: 25000, goldMs: 19500,
    pattern: ['gap_triple', 'platform_wide', 'loop', 'gap_medium', 'barrier_high', 'ramp_large'] },
  { id: 14, name: 'Toundra Fracturée', environment: 'arctic', bronzeMs: 33500, silverMs: 26500, goldMs: 20500,
    pattern: ['platforms_separated', 'gap_large', 'loop_inverse', 'tunnel_narrow', 'ramp_large', 'gap_huge'] },
  { id: 15, name: 'Glacier Extrême', environment: 'arctic', bronzeMs: 31000, silverMs: 24500, goldMs: 19000,
    pattern: ['section_challenge_extreme', 'loop', 'gap_triple', 'platform_narrow', 'ramp_large'] },

  { id: 16, name: 'Blizzard Absolu', environment: 'arctic', bronzeMs: 36500, silverMs: 28500, goldMs: 22000,
    pattern: ['flip_gap_double', 'loop_series', 'gap_huge', 'platforms_alternating', 'ramp_large', 'tunnel_low_ceiling'] },
  { id: 17, name: 'Skyline Ultime', environment: 'neon_city', bronzeMs: 37000, silverMs: 29000, goldMs: 22500,
    pattern: ['loop_series', 'gap_triple', 'wall_inclined', 'flip_gap_single', 'platform_tiny_landing', 'ramp_large'] },
  { id: 18, name: 'Forge Infernale', environment: 'industrial', bronzeMs: 36000, silverMs: 28000, goldMs: 21500,
    pattern: ['section_challenge_extreme', 'gap_huge', 'loop', 'flip_gap_double', 'platforms_alternating'] },
  { id: 19, name: 'Abîme de Magma', environment: 'volcano', bronzeMs: 39000, silverMs: 30500, goldMs: 23500,
    pattern: ['flip_gap_double', 'loop_series', 'gap_triple', 'tunnel_low_ceiling', 'platform_tiny_landing', 'ramp_large'] },
  { id: 20, name: 'Zénith Impossible', environment: 'sky', bronzeMs: 45000, silverMs: 35000, goldMs: 27000,
    pattern: ['loop_series', 'flip_gap_double', 'section_challenge_extreme', 'gap_huge', 'platforms_alternating', 'loop', 'flip_gap_single'] },
];

export function getLevel(id: number): LevelDefinition {
  return LEVELS.find((l) => l.id === id) ?? LEVELS[0];
}
