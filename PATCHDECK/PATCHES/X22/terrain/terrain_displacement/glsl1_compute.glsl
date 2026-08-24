float noise(vec4 p){

	float n = TDPerlinNoise(vec4(p));
	n = abs(n);
	n = exp(-n * u_exponent);
return n;
}

mat2 rot(float a){
a = radians(a);
float s = sin(a), c = cos(a);
return mat2(c,-s,s,c);
}

void rotate3D(inout vec3 p, vec3 a) {
    p.yz = rot(a.x) * p.yz;
    p.xz = rot(a.y) * p.xz;
    p.xy = rot(a.z) * p.xy;
}

float exp_fbm(vec3 p){
//----transforms-----//
rotate3D(p, u_rot);
p *= 1.0/u_period;
p *= u_scale;
p -= u_translate.xyz;

vec4 pos = vec4(p, u_translate.w);

float h_gain = u_h_gain;
float h_spread = u_h_spread;

float w = 1.0;
float f = 1.0;
float n = 0.0;

for(int i = 0; i < u_harmonics; i++)
	{
	n += noise(pos * f) * w;
	w *= h_gain - exp(-n * u_h_exp) * h_gain;
	f *= h_spread;
	pos.w -= w * u_warp;
	
	}

return n;
}

void main() {
	const uint id = TDIndex();
	if(id >= TDNumElements())
		return;
		
	vec3 p = TDIn_P();
	vec3 norm = TDIn_N();
	float displace = exp_fbm(p);
	
	p += displace * norm  * u_amp;
	//outputs
	P[id] = p;
	displaceMap[id] = displace * 0.8;
}
