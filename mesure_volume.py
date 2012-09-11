'''
VOLUME CALCULATION STL binary MODELS
Author: Mar Canet (mar.canet@gmail.com) - september 2012
Description: useful to calculate cost in a 3D printing ABS or PLA usage
'''
import struct
import sys

normals = []
points = []
triangles = []
bytecount = []

fb = [] # debug list

# Calculate volume fo the 3D mesh using Tetrahedron volume
# based in: http://stackoverflow.com/questions/1406029/how-to-calculate-the-volume-of-a-3d-mesh-object-the-surface-of-which-is-made-up
def signedVolumeOfTriangle(p1, p2, p3):
    v321 = p3[0]*p2[1]*p1[2];
    v231 = p2[0]*p3[1]*p1[2];
    v312 = p3[0]*p1[1]*p2[2];
    v132 = p1[0]*p3[1]*p2[2];
    v213 = p2[0]*p1[1]*p3[2];
    v123 = p1[0]*p2[1]*p3[2];
    return (1.0/6.0)*(-v321 + v231 + v312 - v132 - v213 + v123);

def unpack (f, sig, l):
    s = f.read (l)
    fb.append(s)
    return struct.unpack(sig, s)

def read_triangle(f):
    n = unpack(f,"<3f", 12)
    p1 = unpack(f,"<3f", 12)
    p2 = unpack(f,"<3f", 12)
    p3 = unpack(f,"<3f", 12)
    b = unpack(f,"<h", 2)

    normals.append(n)
    l = len(points)
    points.append(p1)
    points.append(p2)
    points.append(p3)
    triangles.append((l, l+1, l+2))
    bytecount.append(b[0])
    
    return signedVolumeOfTriangle(p1,p2,p3)

def read_length(f):
    length = struct.unpack("@i", f.read(4))
    return length[0]

def read_header(f):
    f.seek(f.tell()+80)

def main(infilename):

    totalVolume = 0
    try:
        f = open ( infilename, "rb")
	
        read_header(f)
        l = read_length(f)
        try:
            while True:
                totalVolume +=read_triangle(f)
        except Exception, e:
            print "End calculate triangles volume"
        print len(normals), len(points), len(triangles), l, 
        print "Total volume:", (totalVolume/1000),"cm3"
    except Exception, e:
        print e

if __name__ == '__main__':
	if len(sys.argv)==1:
		print "Define model to calculate volume ej: python mesure_volume.py torus.stl"
	else:
		main(sys.argv[1])