uniform float uRandom;
uniform float uNumPoints;
uniform vec3 uRadius;
uniform int uRandDist;

#define PI 3.141592653589793;

void createPoint(in vec2 vUV)
{
    int texRes = int(uTD2DInfos[0].res.w);
	int pointNum = int(vUV.s * texRes) + int(vUV.t * texRes) * texRes;
    vec3 point = vec3(0.0);
	vec4 rnd = abs(texture(sTD2DInputs[0], vUV));
	vec3 radius = uRadius;
	float phi, theta = 0.0;
	float twoPi = 2.0 * PI;
	if (uRandDist == 0)
	{
		float gRatio = (1.0 + pow(5.0,0.5))/2.0;
		phi = acos(1.0 - (2.0 * pointNum) / (texRes * texRes));
		theta = twoPi * pointNum / gRatio;
	} else
	{
		float twoPi = 2.0 * PI;
		theta = twoPi * rnd.s;
		phi = acos(2*rnd.t - 1.0);
	}
	point.x = cos(theta) * sin(phi);
	point.y = sin(theta) * sin(phi);
	point.z = cos(phi);
	point *= radius;
	gPoint.pos = point;
	gPoint.norm = point;
}
