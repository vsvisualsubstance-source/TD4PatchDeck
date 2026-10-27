// cut_glsl v4 — taglio a righe / colonne / quadrati / mattoni, dimensioni irregolari, scorrimento
// uCut  = modo (0 off, 1 righe, 2 colonne, 3 quadrati, 4 mattoni), colonne, righe, spostamento
// uAnim = passo (kick o tempo), buchi 0-1, seme del livello, spinta del kick
// uJit  = irregolarità 0-1, dettaglio, forme animate (0/1), -
// uScroll = fase, direzione (0 segue il taglio, 1 orizz, 2 vert, 3 misto),
//           schema (0 uniforme, 1 alternato, 2 casuale), verso (+1 / -1)
uniform vec4 uCut;
uniform vec4 uAnim;
uniform vec4 uJit;
uniform vec4 uScroll;

out vec4 fragColor;

float cutHash(vec2 p)
{
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float cutNoise(float x, float seed)
{
	float i = floor(x);
	float f = fract(x);
	float a = cutHash(vec2(i, seed));
	float b = cutHash(vec2(i + 1.0, seed));
	float u = f * f * (3.0 - 2.0 * f);
	return mix(a, b, u);
}

// deformazione monotona: le celle cambiano dimensione ma restano in ordine
float cutWarp(float x, float amt, float freq, float seed)
{
	return x + amt * (cutNoise(x * freq, seed) - 0.5) / freq;
}

void main()
{
	vec2 uv = vUV.st;
	float mode = floor(uCut.x + 0.5);
	vec2 n = max(vec2(1.0), uCut.yz);
	float step = floor(uAnim.x);
	float s = step + uAnim.z * 17.0;

	float jamt = clamp(uJit.x, 0.0, 1.0) * 0.6;
	vec2 jf = max(vec2(1.0), n * max(uJit.y, 0.01));
	float js = uAnim.z * 3.1 + (uJit.z > 0.5 ? step : 0.0);
	vec2 w = vec2(cutWarp(uv.x, jamt, jf.x, js + 1.0),
	              cutWarp(uv.y, jamt, jf.y, js + 7.0));

	vec2 cell = floor(w * n);
	if (mode < 1.5) {
		cell.x = 0.0;
	} else if (mode < 2.5) {
		cell.y = 0.0;
	} else if (mode > 3.5) {
		float shift = cutHash(vec2(cell.y, js + 13.0));
		cell.x = floor(w.x * n.x + shift);
	}

	float r1 = cutHash(cell + vec2(s * 1.37, s * 0.71));
	float r2 = cutHash(cell.yx + vec2(5.0 + s * 2.11, 3.0 - s * 0.53));
	float r3 = cutHash(cell * 1.91 + vec2(s * 0.37, 11.0));

	float amt = uCut.w * (1.0 + uAnim.w);
	vec2 off = vec2(0.0);
	if (mode < 0.5) {
		off = vec2(0.0);
	} else if (mode < 1.5) {
		off.x = (r1 - 0.5) * amt;
	} else if (mode < 2.5) {
		off.y = (r1 - 0.5) * amt;
	} else if (mode < 3.5) {
		off = (vec2(r1, r2) - 0.5) * amt;
	} else {
		off = vec2(r1 - 0.5, (r2 - 0.5) * 0.2) * amt;
	}

	// scorrimento continuo dentro le celle
	float dm = floor(uScroll.y + 0.5);
	float r4 = cutHash(cell * 0.73 + vec2(uAnim.z * 5.3, 29.0));
	vec2 dir = vec2(1.0, 0.0);
	if (dm < 0.5) {
		if (mode > 1.5 && mode < 2.5) {
			dir = vec2(0.0, 1.0);
		}
	} else if (dm < 1.5) {
		dir = vec2(1.0, 0.0);
	} else if (dm < 2.5) {
		dir = vec2(0.0, 1.0);
	} else {
		dir = (r4 < 0.5) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
	}
	float pat = floor(uScroll.z + 0.5);
	float idx = (mode < 1.5) ? cell.y : ((mode < 2.5) ? cell.x : (cell.x + cell.y));
	float k = 1.0;
	if (pat > 0.5 && pat < 1.5) {
		k = (mod(idx, 2.0) < 0.5) ? 1.0 : -1.0;
	} else if (pat > 1.5) {
		float r5 = cutHash(cell + vec2(uAnim.z * 7.7, 41.0));
		k = sign(r5 - 0.5) * (0.3 + 1.4 * abs(r5 - 0.5));
	}
	off += dir * (k * uScroll.w * uScroll.x);

	vec4 color = texture(sTD2DInputs[0], fract(uv + off));
	if (mode > 0.5 && r3 < uAnim.y) {
		color = vec4(0.0);
	}
	fragColor = color;
}
