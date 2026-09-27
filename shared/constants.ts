// Constantes de simulation partagées client/serveur.
// Tout ce qui touche à la génération du terrain doit rester identique
// des deux côtés pour que la coop reste cohérente (même seed => même montagne).

export const WORLD_RADIUS = 220;
export const SUMMIT_HEIGHT = 170;
export const SPIRAL_TURNS = 2.4;
export const SPIRAL_PATH_WIDTH = 0.4; // radians, largeur angulaire du chemin praticable
export const SPIRAL_CARVE_DEPTH = 14; // profondeur du "sentier" creusé dans le relief

export const WALK_MAX_SLOPE_DEG = 34;
export const CLIMB_MAX_SLOPE_DEG = 88;

export const GRAVITY = 26;
export const WALK_SPEED = 5.2;
export const RUN_SPEED = 8.4;
export const AIR_CONTROL = 2.4;
export const JUMP_SPEED = 8.6;
export const JUMP_STAMINA_COST = 10;
export const CLIMB_SPEED = 3.4;
export const GRAB_REACH = 1.35;
export const WALL_STANDOFF = 0.55;
export const SLIP_SPEED = -6;

export const MAX_STAMINA = 100;
export const STAMINA_CLIMB_DRAIN = 11;
export const STAMINA_CLIMB_DRAIN_STEEP_MULT = 1.6;
export const STAMINA_SPRINT_DRAIN = 9;
export const STAMINA_REGEN_GROUND = 20;
export const STAMINA_REGEN_LEDGE = 5;
export const STAMINA_EXHAUST_LOCK_S = 1.6;

export const MAX_HUNGER = 100;
export const HUNGER_DRAIN_PER_S = 0.12;
export const STARVE_HEALTH_DRAIN = 3;
export const BERRY_HUNGER_RESTORE = 35;

export const MAX_HEALTH = 100;
export const SAFE_FALL_DISTANCE = 6;
export const FALL_DAMAGE_PER_UNIT = 4.2;
export const HEALTH_REGEN_PER_S = 1;

export const COLD_ALTITUDE_THRESHOLD = 0.58; // fraction du sommet
export const COLD_RATE = 9;
export const COLD_REGEN = 14;
export const COLD_HEALTH_DRAIN = 5;

export const DOWNED_TIME_S = 30;
export const REVIVE_RADIUS = 2.4;
export const REVIVE_HEALTH = 40;
export const RESPAWN_HEALTH = 55;

export const CHALK_DURATION_S = 20;
export const CHALK_DRAIN_MULT = 0.45;

export const CHECKPOINT_COUNT = 7;
export const ITEM_DENSITY_RADIUS_STEP = 18;

export const DEFAULT_PORT = 8787;
export const MAX_PLAYERS_PER_ROOM = 4;
export const PROTOCOL_VERSION = 1;

export const WALK_MAX_SLOPE = (WALK_MAX_SLOPE_DEG * Math.PI) / 180;
export const CLIMB_MAX_SLOPE = (CLIMB_MAX_SLOPE_DEG * Math.PI) / 180;
