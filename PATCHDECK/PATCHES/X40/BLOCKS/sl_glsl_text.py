// taglio a bande, deriva continua (nessuna oscillazione)
// uP: x = numero bande  y = spostamento  z = tempo  w = irregolarita'
// uQ: x = modalita' (0 = orizzontali, 1 = verticali, 2 = entrambe)
out vec4 fragColor;
uniform vec4 uP;
uniform vec4 uQ;

float hash(float n) { return fract(sin(n * 127.1) * 43758.5453); }

// la deriva cresce nel tempo, il fract la fa rientrare dall'altro lato
float bandShift(float b)
{
    float calmo = 0.3 + 0.7 * hash(b + 5.0);            // stesso verso
    float rotto = (hash(b + 9.0) * 2.0 - 1.0) * 2.0;    // versi misti
    return uP.z * mix(calmo, rotto, uP.w) * uP.y;
}

void main()
{
    vec2 uv = vUV.st;
    vec2 st = uv;
    int  mode = int(uQ.x + 0.5);
    float bands = max(2.0, uP.x);

    if (mode == 0 || mode == 2) {
        float b = floor(uv.y * bands);
        st.x = fract(st.x + bandShift(b));
    }
    if (mode == 1 || mode == 2) {
        float b = floor(uv.x * bands) + 137.0;   // indice dalla X ORIGINALE
        st.y = fract(st.y + bandShift(b));
    }

    fragColor = TDOutputSwizzle(texture(sTD2DInputs[0], st));
}
