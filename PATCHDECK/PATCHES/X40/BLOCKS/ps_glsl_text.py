// ordinamento a trasposizione pari-dispari, per colonne
// sTD2DInputs[0] = immagine viva   sTD2DInputs[1] = stato del frame prima
// uP: x = fase (0/1)  y = soglia luminanza  z = rigenerazione
out vec4 fragColor;
uniform vec4 uP;

float lum(vec3 c) { return dot(c, vec3(0.299, 0.587, 0.114)); }

vec4 state(ivec2 p)
{
    vec4 prev = texelFetch(sTD2DInputs[1], p, 0);
    vec4 live = texelFetch(sTD2DInputs[0], p, 0);
    return mix(prev, live, uP.z);
}

void main()
{
    ivec2 res = textureSize(sTD2DInputs[1], 0);
    ivec2 uv  = ivec2(gl_FragCoord.xy);
    vec4 cur  = state(uv);

    // alternando la fase le coppie sono (0,1)(2,3)... poi (1,2)(3,4)...
    bool lower = ((uv.y + int(uP.x)) % 2 == 0);
    int  oy    = lower ? uv.y + 1 : uv.y - 1;

    if (oy < 0 || oy >= res.y) {
        fragColor = TDOutputSwizzle(cur);
        return;
    }

    vec4 other = state(ivec2(uv.x, oy));
    float a = lum(cur.rgb);
    float b = lum(other.rgb);

    // sotto soglia i pixel non partecipano: decide DOVE si spezza
    if (a > uP.y && b > uP.y) {
        if (lower  && a > b) cur = other;
        if (!lower && b > a) cur = other;
    }

    fragColor = TDOutputSwizzle(cur);
}
