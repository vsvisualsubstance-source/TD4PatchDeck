uniform float uRandom;
uniform float uNumPoints;
uniform vec3 uRadius;
uniform int uRandDist;
uniform int uOrientation;

#define PI 3.141592653589793;

void createPoint(in vec2 vUV)
{
    int texRes = int(uTD2DInfos[0].res.w);
	int	pointNum = int(vUV.s * texRes) + int(vUV.t * texRes) * texRes;
    vec3 point = vec3(0.0);
	vec4 rnd = texture(sTD2DInputs[0], vUV);
	
	float twoPi = 2.0 * PI;
	float r = sqrt((rnd.x + 1.0)/2);
	float a = (rnd.y + 1.0)/2.0 * twoPi;
	point.x = r * uRadius.x * cos(a);
	point.y = r * uRadius.y * sin(a);
	
	// normals
	int axis = int(mod(uOrientation+2,3));
	vec3 norm = vec3(0.0);
	norm[axis] = 1.0;

	// orientation
	if (uOrientation == 1)
	{
		point = point.zxy;
	}
	else if (uOrientation == 2)
	{
		point = point.xzy;
	}

	gPoint.pos = point;
	gPoint.norm = norm;
}