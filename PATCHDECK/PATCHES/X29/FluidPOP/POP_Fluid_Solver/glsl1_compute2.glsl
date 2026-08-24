// ===== Particles_Advect.glsl (POP) =====
// Entrée 0 : particules      (P)
// Entrée 1 : grille de taille R^3 (U, P au centre des voxels)
// Uniforms requis : SimRes (uint), SimSizex/y/z (float), dt (float)

uint flatten3(ivec3 c, uint R){
    return uint(c.x) + R * (uint(c.y) + R * uint(c.z));
}

// Interpolation trilineaire de U défini aux centres de voxels
vec3 sampleU_trilinear_grid(vec3 x, vec3 bmin, vec3 inv_h, uint R){
    // coords de grille où les centres sont à (i + 0.5)
    vec3 g = (x - bmin) * inv_h - vec3(0.5);

    ivec3 i0 = ivec3(floor(g));
    ivec3 i1 = i0 + ivec3(1);
    vec3  f  = clamp(fract(g), 0.0, 1.0);

    ivec3 lo = ivec3(0);
    ivec3 hi = ivec3(int(R) - 1);
    i0 = clamp(i0, lo, hi);
    i1 = clamp(i1, lo, hi);

    // lire U dans l'entrée 1 (la grille)
    vec3 c000 = TDIn_U(1, flatten3(ivec3(i0.x, i0.y, i0.z), R));
    vec3 c100 = TDIn_U(1, flatten3(ivec3(i1.x, i0.y, i0.z), R));
    vec3 c010 = TDIn_U(1, flatten3(ivec3(i0.x, i1.y, i0.z), R));
    vec3 c110 = TDIn_U(1, flatten3(ivec3(i1.x, i1.y, i0.z), R));
    vec3 c001 = TDIn_U(1, flatten3(ivec3(i0.x, i0.y, i1.z), R));
    vec3 c101 = TDIn_U(1, flatten3(ivec3(i1.x, i0.y, i1.z), R));
    vec3 c011 = TDIn_U(1, flatten3(ivec3(i0.x, i1.y, i1.z), R));
    vec3 c111 = TDIn_U(1, flatten3(ivec3(i1.x, i1.y, i1.z), R));

    vec3 c00 = mix(c000, c100, f.x);
    vec3 c10 = mix(c010, c110, f.x);
    vec3 c01 = mix(c001, c101, f.x);
    vec3 c11 = mix(c011, c111, f.x);
    vec3 c0  = mix(c00,  c10,  f.y);
    vec3 c1  = mix(c01,  c11,  f.y);
    return mix(c0, c1, f.z);
}

void main(){
    const uint id = TDIndex();
    if (id >= TDNumElements()) return;

    // lecture particule (entrée 0)
    vec3 pos = TDIn_P(0, id);

    // constantes grille (passées en uniforms)
    uint R   = max(SimRes, 1u);
    vec3 bmin = vec3(-0.5*SimSizex, -0.5*SimSizey, -0.5*SimSizez);
    vec3 size = vec3( SimSizex,      SimSizey,      SimSizez );
    vec3 h    = size / float(R);
    vec3 inv_h = 1.0 / h;

    // échantillonner la vitesse grille au point pos (trilinéaire exact)
    vec3 v = sampleU_trilinear_grid(pos, bmin, inv_h, R);

    // advection simple (Euler)
    pos += dt * v;
    Speed[id] = v;

    // clamp doux au domaine
    const float eps = 1e-4;
    vec3 bmax = bmin + size;
    pos = clamp(pos, bmin + eps, bmax - eps);

    // écrire sorties (tu peux aussi stocker v si tu veux le visualiser)
    P[id] = pos;
    // vit[id] = v; // si tu as créé cet attribut
}
