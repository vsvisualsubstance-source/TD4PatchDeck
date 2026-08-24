void main() {
    const uint id = TDIndex();
    if (id >= TDNumElements())
        return;

    uint R = max(SimRes, 1u);
    uint N = R*R*R;

    if (id < N) {
        // 1D -> 3D indices (i,j,k) dans [0..R-1]
        uint i =  id              % R;
        uint j = (id / R)         % R;
        uint k =  id / (R*R);

        // Domaine centré
        vec3 bmin = vec3(-0.5*SimSizex, -0.5*SimSizey, -0.5*SimSizez);
        vec3 size = vec3( SimSizex,      SimSizey,      SimSizez );
        vec3 h    = size / float(R); // taille cellule

        // Centre de la cellule (i,j,k)
        vec3 center = bmin + (vec3(i, j, k) + 0.5) * h;

        // Écrit la position
        P[id] = center;

        // Normale discrète des bords (vers l'extérieur)
        vec3 bnd = vec3(
            (i==0u   ? -1.0 : (i==R-1u ?  1.0 : 0.0)),
            (j==0u   ? -1.0 : (j==R-1u ?  1.0 : 0.0)),
            (k==0u   ? -1.0 : (k==R-1u ?  1.0 : 0.0))
        );
        BndN[id] = bnd;

        // Flag = 1 si cellule de bord, sinon 0 (cohérent avec BndN)
        Flag[id] = any(notEqual(bnd, vec3(0.0))) ? 1u : 0u;

        // Indices (pour les stencils)
        ijk[id] = vec3(i, j, k);

    } else {
        // Points excédentaires: on les laisse tels quels
        //P[id] = TDIn_P();
    }
}
