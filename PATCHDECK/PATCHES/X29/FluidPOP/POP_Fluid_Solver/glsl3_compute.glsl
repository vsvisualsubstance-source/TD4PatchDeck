// --- C) NORMALISATION ---
// Entrée 0 : voxels (lit AccV/AccW et écrit U)

void main(){
    const uint id = TDIndex();
    if (id >= TDNumElements()) return;

    vec3  acc = AccV[id];
    float w   = AccW[id];
    float inv = (w > 1e-12) ? (1.0 / w) : 0.0;

    v_input[id] = acc * inv;  // vitesse grille finale
}
