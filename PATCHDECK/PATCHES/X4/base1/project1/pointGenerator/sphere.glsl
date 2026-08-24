uniform float uRandom;
uniform float uNumPoints;
uniform vec3 uRadius;

#define PI 3.141592653589793;

void createPoint(in vec2 vUV)
{
    int texRes = int(uTD2DInfos[0].res.w);
	int pointNum = int(vUV.s * texRes) + int(vUV.t * texRes) * texRes;
    vec3 point = vec3(0.0);
	vec4 rnd = abs(texture(sTD2DInputs[0], vUV));

	float twoPi = 2.0 * PI;
	float theta = twoPi * rnd.s;
	float phi = acos(2*rnd.t - 1.0);
	float third = 1.0 / 3.0;
	vec3 radius = pow(vec3(rnd.p), vec3(third)) * uRadius;
	point.x = cos(theta) * sin(phi);
	point.y = sin(theta) * sin(phi);
	point.z = cos(phi);
	point *= radius;
	gPoint.pos = point;
	gPoint.norm = point;
}
