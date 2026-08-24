uniform float uRandom;
uniform float uNumPoints;
uniform int uOrientation;
uniform vec2 uRadius;

#define PI 3.141592653589793;

void createPoint(in vec2 vUV)
{
    int texRes = int(uTD2DInfos[0].res.w);
	int	pointNum = int(vUV.s * texRes) + int(vUV.t * texRes) * texRes;
    vec3 point = vec3(0.0);
	vec4 rnd = texture(sTD2DInputs[0], vUV);
	int axis = int(mod(uOrientation+2,3));
	rnd.xy *= 2*PI;
	point.x = (uRadius.x + uRadius.y * cos(rnd.s))*cos(rnd.t);
	point.y = (uRadius.x + uRadius.y * cos(rnd.s))*sin(rnd.t);
	point.z = (uRadius.y * sin(rnd.s));

	vec3 norm = vec3(0.0);
	vec3 refPoint = vec3(0.0);
	refPoint.x = uRadius.x * cos(rnd.t);
	refPoint.y = uRadius.x * sin(rnd.t);
	norm = point - refPoint;

	if (uOrientation == 1)
	{
		point = point.zyx;
	}
	else if (uOrientation == 2)
	{
		point = point.xzy;
	}
	gPoint.pos = point;
	gPoint.norm = norm;
}