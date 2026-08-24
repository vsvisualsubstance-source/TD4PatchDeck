uniform float uRandom;
uniform float uNumPoints;
uniform vec3 uSize;


void createPoint(in vec2 vUV)
{
    int texRes = int(uTD2DInfos[0].res.w);
	int	pointNum = int(vUV.s * texRes) + int(vUV.t * texRes) * texRes;
    vec3 point = vec3(0.0);
	vec4 rnd = texture(sTD2DInputs[0], vUV);
	float side = (rnd.w + 2) * 3;
	int axis = int(side) % 3;
	vec3 norm = vec3(0.0);
	norm[axis] = (fract(side) >= 0.5) ? 1 : -1;
	norm[axis] = rnd[axis];
	point = (rnd.xyz * uSize * uRandom);
	gPoint.pos = point;
	gPoint.norm = norm;
}
