// quantizzazione colore + dithering ordinato 4x4 (Bayer)
// uP: x = livelli per canale  y = intensita' dithering
out vec4 fragColor;
uniform vec4 uP;

const float bayer[16] = float[16](
     0.0,  8.0,  2.0, 10.0,
    12.0,  4.0, 14.0,  6.0,
     3.0, 11.0,  1.0,  9.0,
    15.0,  7.0, 13.0,  5.0
);

void main()
{
    vec4 src = texture(sTD2DInputs[0], vUV.st);
    float levels = max(2.0, uP.x);

    int bx = int(mod(gl_FragCoord.x, 4.0));
    int by = int(mod(gl_FragCoord.y, 4.0));
    float threshold = (bayer[by * 4 + bx] + 0.5) / 16.0 - 0.5;

    vec3 col = src.rgb + threshold * uP.y / levels;     // dither PRIMA
    col = clamp(floor(col * levels + 0.5) / levels, 0.0, 1.0);

    fragColor = TDOutputSwizzle(vec4(col, src.a));
}
