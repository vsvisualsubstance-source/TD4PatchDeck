// --- B) SPLAT DES VITESSES POINTS -> GRILLE ---
// Entrée 0 : voxels (on écrit dans AccV/AccW de la grille)
// Entrée 1 : points avec attribut v (vec3) à projeter
// (Optionnel) Entrées 2 : 1 point avec attribut NumPoints (pas nécessaire si 'Number of Threads' = Other Input 1)
// Uniforms requis : SimRes (uint), SimSizex/y/z (float)
#extension GL_EXT_shader_atomic_float : require

uint flatten3(ivec3 c, uint R){
    return uint(c.x) + R * (uint(c.y) + R * uint(c.z));
}

struct TriliInfo { ivec3 i0; vec3 f; };

TriliInfo triliInfo(vec3 x, vec3 bmin, vec3 size, uint R){
    TriliInfo t;
    vec3 h = size / float(R);
    vec3 g = (x - bmin) / h - vec3(0.5);
    t.i0 = ivec3(floor(g));
    t.f  = clamp(fract(g), 0.0, 1.0);
    return t;
}

void splatV_trilinear_grid(vec3 p, vec3 v, vec3 bmin, vec3 size, uint R){
    vec3 bmax = bmin + size;
    // on ignore les points hors domaine
    if (any(lessThan(p, bmin)) || any(greaterThan(p, bmax))) return;

    TriliInfo t = triliInfo(p, bmin, size, R);
    ivec3 lo = ivec3(0), hi = ivec3(int(R)-1);
    ivec3 i0 = clamp(t.i0, lo, hi);
    vec3  f  = t.f;

    // 8 voisins, mêmes poids que l’advection trilinéaire (gather)
    for (int dz=0; dz<=1; ++dz){
        float wz = (dz==0) ? (1.0 - f.z) : f.z;
        int z = clamp(i0.z + dz, lo.z, hi.z);
        for (int dy=0; dy<=1; ++dy){
            float wy = (dy==0) ? (1.0 - f.y) : f.y;
            int y = clamp(i0.y + dy, lo.y, hi.y);
            for (int dx=0; dx<=1; ++dx){
                float wx = (dx==0) ? (1.0 - f.x) : f.x;
                int x = clamp(i0.x + dx, lo.x, hi.x);

                float w = wx * wy * wz;
                uint idx = flatten3(ivec3(x,y,z), R);

                // Accumulation atomique (evite les races si plusieurs points touchent le même voxel)
                atomicAdd(AccV[idx].x, v.x * w);
                atomicAdd(AccV[idx].y, v.y * w);
                atomicAdd(AccV[idx].z, v.z * w);
                atomicAdd(AccW[idx],    w);
            }
        }
    }
}

void main(){
    const uint id = TDIndex();
    // IMPORTANT : règle "Number of Threads" -> Other Input = 1 (points). TDNumElements() == nb de points
    if (id >= TDNumElements()) return;

    // Domaine de la grille (anisotrope OK)
    uint R   = max(SimRes, 1u);
    vec3 size = vec3(SimSizex, SimSizey, SimSizez);
    vec3 bmin = vec3(-0.5*SimSizex, -0.5*SimSizey, -0.5*SimSizez);

    // Lire le point id sur l'ENTRÉE 1
    vec3 p = TDIn_P(1, id);
    vec3 v = TDIn_v(1, id);   // ton attribut vitesse sur l’entrée 1

    // Splat vers la grille (entrée 0 / buffers de sortie)
    splatV_trilinear_grid(p, v, bmin, size, R);
}
