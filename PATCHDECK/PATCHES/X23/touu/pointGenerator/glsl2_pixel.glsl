struct Point
{
	vec3 pos;
	vec3 norm;
};

Point gPoint;

#include "createPoint"

layout(location = 0) out vec4 fragColor;
layout(location = 1) out vec4 normColor;

void main()
{
	vec4 point = vec4(0.0);
	vec4 normals = vec4(0.0);
	createPoint(vUV.st);
	point.xyz = gPoint.pos;
	normals.xyz = gPoint.norm;
	normColor = TDOutputSwizzle(normals);
	point.w = 1;
	fragColor = TDOutputSwizzle(point);
}