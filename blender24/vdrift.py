#!BPY
# -*- coding: iso-8859-1 -*-

######################################################
# VDrift Module(used by import/export-joe/jpk)
# By: NaN, based on JOE exporter by Joe Venzon
#	  and   MD2 importer by Bob Holcomb
# Date:	24 JAN 10
# Ver:	0.1
######################################################

import Blender
from Blender.Mathutils import Vector
from Blender import Group
import struct

JOE_MAX_TRIANGLES = 4096
JOE_MAX_VERTICES = 2048
JOE_MAX_TEXCOORDS = 2048
JOE_MAX_NORMALS = 2048
JOE_MAX_FRAMES = 512
JOE_VERSION = 3
#JOE_MAX_FRAMESIZE=(JOE_MAX_VERTICES * 24 + 128)

class joe_vertex:
	__slots__ = 'x', 'y', 'z'
	binary_format = "<fff"
	binary_size = struct.calcsize(binary_format)
	
	def __init__(self, x = 0.0, y = 0.0, z = 0.0):
		self.x, self.y, self.z = x, y, z
	
	def co(self):
		return self.x, self.y, self.z
	
	def load(self, file):
		temp_data = file.read(self.binary_size)
		data = struct.unpack(self.binary_format, temp_data)
		self.x = data[0]
		self.y = data[1]
		self.z = data[2]
		return self
	
	def save(self, file):
		data = struct.pack(self.binary_format, self.x, self.y, self.z)
		file.write(data)

class joe_texcoord(object):
	__slots__ = 'u', 'v'
	binary_format = "<2f" #little-endian (<), 2 float
	binary_size = struct.calcsize(binary_format)
	
	def __init__(self, u = 0.0, v = 0.0):
		self.u, self.v = u, v
	
	def uv(self):
		return self.u, self.v
	
	def load (self, file):
		temp_data = file.read(self.binary_size)
		data = struct.unpack(self.binary_format, temp_data)
		self.u = data[0]
		self.v = 1.0 - data[1]
		return self
	
	def save(self, file):
		data = struct.pack(self.binary_format, self.u, 1 - self.v)
		file.write(data)

class joe_face(object):
	__slots__ = 'vertex_index', 'normal_index', 'texture_index'
	binary_format = "<3h3h3h" #little-endian (<), 3 short, 3 short
	binary_size = struct.calcsize(binary_format)
   
	def __init__(self):
		self.vertex_index = [0, 0, 0]
		self.normal_index = [0, 0, 0]
		self.texture_index = [0, 0, 0]
	
	def load (self, file):
		temp_data = file.read(self.binary_size)
		data = struct.unpack(self.binary_format, temp_data)
		self.vertex_index = [data[0], data[1], data[2]]
		self.normal_index = [data[3], data[4], data[5]]
		self.texture_index = [data[6], data[7], data[8]]
		return self
	
	def save(self, file):
		data = struct.pack(self.binary_format, self.vertex_index[0],self.vertex_index[1],self.vertex_index[2],self.normal_index[0],self.normal_index[1],self.normal_index[2],self.texture_index[0],self.texture_index[1],self.texture_index[2])
		file.write(data)

class joe_frame(object):
	__slots__ = 'num_vertices', 'num_normals', 'num_texcoords', 'faces', 'verts', 'texcoords', 'normals'
	binary_format = "<3i"
	binary_size = struct.calcsize(binary_format)

	def __init__(self):
		self.num_vertices = 0
		self.num_texcoords = 0
		self.num_normals = 0
		self.faces = []
		self.verts = []
		self.texcoords = []
		self.normals = []

	def load(self, file):
		# header
		temp_data = file.read(self.binary_size)
		data = struct.unpack(self.binary_format, temp_data)
		self.num_vertices = data[0]
		self.num_texcoords = data[1]
		self.num_normals = data[2]
		# mesh data
		for i in range(self.num_vertices):
			self.verts.append(joe_vertex().load(file))
		for i in range(self.num_normals):
			self.normals.append(joe_vertex().load(file))
		for i in range(self.num_texcoords):
			self.texcoords.append(joe_texcoord().load(file))
		return self
	
	def save(self, file):
		# header
		data = struct.pack(self.binary_format, self.num_vertices, self.num_texcoords, self.num_normals)
		file.write(data)
		# mesh data
		for i in range(self.num_vertices):
			self.verts[i].save(file)
		for i in range(self.num_normals):
			self.normals[i].save(file)
		for i in range(self.num_texcoords):
			self.texcoords[i].save(file)
	
	def from_mesh(self, obj):
		# mesh setup
		mesh = get_tri_mesh(obj)
		mesh.transform(obj.matrixWorld)
		# mesh load
		normals = indexed_set()
		vertices = indexed_set()
		texcoords = indexed_set()
		for f in mesh.faces:
			jf = joe_face()
			# normals
			if f.smooth:
				jf.normal_index = [normals.get((v.no.x, v.no.y, v.no.z)) for v in f.verts]
			else:
				jf.normal_index = [normals.get((f.no.x, f.no.y, f.no.z))] * 3
			# vertices
			jf.vertex_index = [vertices.get((v.co.x, v.co.y, v.co.z)) for v in f.verts]
			# texture coordinates
			if mesh.faceUV:
				jf.texture_index = [texcoords.get((uv.x, uv.y)) for uv in f.uv]
			else:
				jf.texture_index = [texcoords.get((0.0, 0.0))] * 3
			self.faces.append(jf)
		self.normals = [joe_vertex(n[0], n[1], n[2]) for n in normals.list]
		self.verts = [joe_vertex(v[0], v[1], v[2]) for v in vertices.list]
		self.texcoords = [joe_texcoord(uv[0], uv[1]) for uv in texcoords.list]
		self.num_normals = len(self.normals)
		self.num_texcoords = len(self.texcoords)
		self.num_vertices = len(self.verts)
		return self

	def duplicate_verts_with_multiple_normals(self):
		#print len(self.verts)
		face_vert = {}
		verts = []
		for f in self.faces:
			for i in range(3):
				vn = f.vertex_index[i], f.normal_index[i]
				if vn not in face_vert:
					verts.append(self.verts[f.vertex_index[i]])
					vi = len(verts) - 1
					f.vertex_index[i] = vi
					face_vert[vn] = vi
				else:
					f.vertex_index[i] = face_vert[vn]
		self.verts = verts
		#print len(self.verts)
	
	def remove_degenerate_faces(self):
		#print len(self.faces)
		faces = []
		for f in self.faces:
			vi = f.vertex_index
			if vi[0] != vi[1] and vi[1] != vi[2] and vi[0] != vi[2]:
				faces.append(f)
		self.faces = faces
		#print len(self.faces)
	
	def to_mesh(self, name, image):
		self.remove_degenerate_faces()
		self.duplicate_verts_with_multiple_normals()
		mesh = Blender.Mesh.New()
		mesh.properties['joename'] = name
		mesh.verts.extend([Vector(v.co()) for v in self.verts])
		# set normals
		for f in self.faces:
			for i in range(3):
				mesh.verts[f.vertex_index[i]].no = Vector(self.normals[f.normal_index[i]].co())
		# set faces
		mesh.faces.extend([f.vertex_index for f in self.faces], ignoreDups=True)
		# set texture coordinates
		for i in range(len(mesh.faces)):
			sf = self.faces[i]
			mf = mesh.faces[i]
			# fix face indices ordering
			i = (0, 1, 2)
			if mf.v[0].index == sf.vertex_index[1]:	i = (1, 2, 0)
			elif mf.v[0].index == sf.vertex_index[2]: i = (2, 0, 1)
			# set coordinates
			ti = sf.texture_index[i[0]], sf.texture_index[i[1]], sf.texture_index[i[2]]
			uv = [Vector(self.texcoords[ti[0]].uv()), Vector(self.texcoords[ti[1]].uv()), Vector(self.texcoords[ti[2]].uv())]
			mf.uv = uv
			mf.smooth = 1
			if image != None:
				mf.image = image
		# add to scene
		scn = Blender.Scene.GetCurrent()
		if name:
			return scn.objects.new(mesh, name)
		else:
			return scn.objects.new(mesh)

class joe_obj(object):
	__slots__ = 'ident', 'version', 'num_faces', 'num_frames', 'frames'
	binary_format = "<4i"  #little-endian (<), 4 integers (4i)
	binary_size = struct.calcsize(binary_format)
   
	def __init__(self):
		self.ident = 844121161
		self.version = JOE_VERSION
		self.num_faces = 0
		self.num_frames = 0
		self.frames = []
   
	def load(self, file):
		# header
		temp_data = file.read(self.binary_size)
		data = struct.unpack(self.binary_format, temp_data)
		self.ident = data[0]
		self.version = data[1]
		self.num_faces = data[2]
		self.num_frames = data[3]
		# frames
		for i in range(self.num_frames):
			self.frames.append(joe_frame())
			for j in range(self.num_faces):
				self.frames[i].faces.append(joe_face().load(file))
			self.frames[i].load(file)
		return self
	
	def save(self, file):
		# header
		data = struct.pack(self.binary_format, self.ident, self.version, self.num_faces, self.num_frames)
		file.write(data)
		# frames
		for i in range(self.num_frames):
			for j in range(self.num_faces):
				self.frames[i].faces[j].save(file)
			self.frames[i].save(file)
			
	def to_mesh(self, name, image, num_frames=1):
		frames = []
		for i in range(num_frames):
			Blender.Set('curframe', i)
			frames.append(self.frames[i].to_mesh(name, image))
		return frames[0]
		
	def from_mesh(self, mesh_obj, num_frames=1):
		for i in range(num_frames):
			Blender.Set('curframe', i)
			frame = joe_frame()
			frame.from_mesh(mesh_obj)
			self.frames.append(frame)
		self.num_frames = num_frames
		self.num_faces = len(self.frames[0].faces)
		return self

class joe_pack(object):
	versionstr = 'JPK01.00'
	binary_format = "<2i"  #little-endian (<), 2 integers (2i)
	binary_size = struct.calcsize(binary_format)

	def __init__(self):
		self.numobjs = 0
		self.maxstrlen = 0
		self.joe = {}
		self.list = {}
		self.images = {}
		self.surfaces = []
			
	def load(self, filename):
		# don't change call order
		self.load_list(filename)
		self.load_images(filename)
		self.load_jpk(filename)
		return self
	
	def save(self, filename):
		self.save_jpk(filename)
		self.save_list(filename)
		
	def to_mesh(self):
		trackobject_to_obj_init()
		for name, joe in self.joe.iteritems():
			image = None
			trackobject = self.list.get(name)
			if trackobject:
				imagename = trackobject.values[1]
				image = self.images[imagename]
				obj = joe.to_mesh(name, image)
				me = obj.getData(mesh=1)
				#me.remDoubles(0.0001)
				trackobject.to_obj(obj)
			else:
				print name + ' not in list.txt.'
		
	def from_mesh(self):
		objlist = Blender.Object.Get()
		trackobject_from_obj_init()
		for obj in objlist:
			if obj.getType() == 'Mesh' and not obj.name.startswith('~temp')\
			and len(obj.getData().faces) > 0 and obj.getData().faces[0].image is not None:
				objname = obj.name
				trackobj = trackobject().from_obj(obj)
				# override obj name
				if len(trackobj.values[0]):
					objname = trackobj.values[0]
				# loader expects a joe file
				if not objname.endswith('.joe'):
					objname = objname + '.joe'
					trackobj.values[0] = objname
				self.list[objname] = trackobj
				self.joe[objname] = joe_obj().from_mesh(obj)
				self.maxstrlen = max(self.maxstrlen, len(objname))
			else:
				mesh = obj.getData(mesh=True)
				if 'joename' in mesh.properties:
					print mesh.properties['joename'] + ' was not exported.'
				else:
					print obj.name + ' was not exported.'
		self.numobjs = len(self.joe)
		return self
		
	def load_jpk(self, filename):
		file = open(filename, 'rb')
		# header
		version = file.read(len(self.versionstr))
		temp = file.read(self.binary_size)
		data = struct.unpack(self.binary_format, temp)
		self.numobjs = data[0]
		self.maxstrlen = data[1]
		# fat
		fat = []
		for i in range(self.numobjs):
			temp = file.read(self.binary_size)
			data = struct.unpack(self.binary_format, temp)
			offset = data[0]
			length = data[1]
			name = file.read(self.maxstrlen)
			fat.append((offset, length, stripz(name)))
		# data
		for offset, length, name in fat:
			pos = file.tell()
			delta = offset - pos
			if delta < 0:
				print 'Error reading: ', name, offset
				return
			elif delta > 0:
				file.read(delta)
			joe = joe_obj().load(file)
			self.joe[name] = joe
		file.close()
	
	def save_jpk(self, filename):
		if not Blender.sys.exists(filename):
			open(filename, 'w').close()
		file = open(filename, 'rb+')
		# header
		file.write(self.versionstr)
		data = struct.pack(self.binary_format, self.numobjs, self.maxstrlen)
		file.write(data)
		# allocate fat
		fat_offset = file.tell()
		for i in range(self.numobjs):
			data = struct.pack(self.binary_format, 0, 0)
			file.write(data)
			name = fillz('', self.maxstrlen)
			file.write(name)
		# write data / build fat
		fat = []
		for name, joe in self.joe.iteritems():
			offset = file.tell()
			joe.save(file)
			length = file.tell() - offset
			fat.append((offset, length, name))
		# fill fat
		file.seek(fat_offset)
		for offset, length, name in fat:
			data = struct.pack(self.binary_format, offset, length)
			file.write(data)
			name = fillz(name, self.maxstrlen)
			file.write(name)
		file.close()
		
	def load_list(self, filename):
		dir = Blender.sys.dirname(filename)
		list_path = Blender.sys.join(dir, 'list.txt')
		#debug = open(Blender.sys.join(dir, 'debug.txt'), 'w')
		if not Blender.sys.exists(list_path):
			print list.path + ' not found.'
			return
		# read objects
		list_file = open(list_path)
		line = list_file.readline()
		while line != '':
			if '.joe' in line:
				object = trackobject()
				name = line.strip()
				line = object.read(name, list_file)
				#debug.write(str(object.values)+'\n')
				self.list[object.values[0]] = object
			else:
				line = list_file.readline()
		if len(self.list) == 0:
			print 'Failed to load list.txt.'
		list_file.close()
		#debug.close()
		
	def save_list(self, filename):
		dir = Blender.sys.dirname(filename)
		list_path = Blender.sys.join(dir, 'list.txt')
		file = open(list_path, 'w')
		file.write('17\n\n')
		i = 0
		for name, object in self.list.iteritems():
			file.write('#entry ' + str(i) + '\n')
			object.write(file)
			i = i + 1
		file.close()
		
	def load_images(self, filename):
		dir = Blender.sys.dirname(filename)
		for name, object in self.list.iteritems():
			imagename = object.values[1]
			if imagename not in self.images:
				path = Blender.sys.join(dir, imagename)
				self.images[imagename] = load_image(path)

def trackobject_to_obj_init():
	trackobject.grp_surf = []
	trackobject.grp = {}
	for name in ('mipmap', 'nolighting', 'skybox', 'transparent', 'doublesided', 'collidable', 'shadow'):
		try: trackobject.grp[name] = Group.Get(name).objects
		except: trackobject.grp[name] = Group.New(name).objects

def trackobject_from_obj_init():
	trackobject_to_obj_init()
	trackobject.is_surf = []
	for grp in Group.Get():
		if grp.name.startswith('surface'):
			trackobject.is_surf.append((grp.name.split('-')[-1], set(grp.objects)))
			print grp.name
		elif grp.name == 'mipmap':
			trackobject.is_mipmap = set(grp.objects)
		elif grp.name == 'nolighting':
			trackobject.is_nolighting = set(grp.objects)
		elif grp.name == 'skybox':
			trackobject.is_skybox = set(grp.objects)
		elif grp.name == 'collidable':
			trackobject.is_collidable = set(grp.objects)
		elif grp.name == 'shadow':
			trackobject.is_shadow = set(grp.objects)
		elif grp.name == 'transparent':
			trackobject.is_transparent = set(grp.objects)
		elif grp.name == 'doublesided':
			trackobject.is_doublesided = set(grp.objects)

class trackobject:
	names = ['model', 'texture', 'mipmap', 'lighting', 'skybox', 'blend', 'bump length', 'bump amplitude', 'drivable', 'collidable', 'non treaded', 'treaded', 'roll resistance', 'roll drag', 'shadow', 'clamp', 'surface']
	namemap = dict(zip(names, range(17)))
	
	def __init__(self):
		self.values = ['none', 'none', '1', '0', '0', '0', '1.0', '0.0', '0', '0', '1.0', '0.9', '1.0', '0.0', '0', '0', '0']
	
	def read(self, name, list_file):
		i = 0
		self.values[i] = name
		while True:
			line = list_file.readline()
			if line == '' or '.joe' in line:
				return line
			elif line.startswith('#') or line.startswith('\n'):
				continue
			else:
				i = i + 1
				self.values[i] = line.strip()
		return line
	
	def write(self, list_file):
		for v in self.values:
			list_file.write(v + '\n')
		list_file.write('\n')
	
	def to_obj(self, sceneobject):
		# set properties (deprecated)
		for name, value in zip(trackobject.names, self.values):
			sceneobject.addProperty(name, value, 'STRING')
		# set group
		if self.values[2] == '1': trackobject.grp['mipmap'].link(sceneobject)
		if self.values[3] == '1': trackobject.grp['nolighting'].link(sceneobject)
		if self.values[4] == '1': trackobject.grp['skybox'].link(sceneobject)
		if self.values[5] == '1': trackobject.grp['transparent'].link(sceneobject)
		elif self.values[5] == '2': trackobject.grp['doublesided'].link(sceneobject)
		if self.values[8] == '1' or self.values[9] == '1': trackobject.grp['collidable'].link(sceneobject)
		if self.values[14] == '1': trackobject.grp['shadow'].link(sceneobject)
		surfid = int(self.values[16])
		while surfid >= len(trackobject.grp_surf):
			surfnum = len(trackobject.grp_surf)
			surfname = 'surface-'+str(surfnum)
			try: grp = Group.Get(surfname).objects
			except: grp = Group.New(surfname).objects
			trackobject.grp_surf.append(grp)
		trackobject.grp_surf[surfid].link(sceneobject)
		return self
	
	# set from object
	def from_obj(self, sceneobject):
		# get ptoperties (deprecated)
		properties = sceneobject.getAllProperties()
		for p in properties:
			if p.name in trackobject.namemap:
				self.values[trackobject.namemap[p.name]] = p.data
		# if texture, mesh properties not set, get them from mesh
		if self.values[0] == 'none':
			self.values[0] = sceneobject.name
		if self.values[1] == 'none':
			self.values[1] = sceneobject.getData().faces[0].image.getName()
		# get group properties
		self.values[2] = '1' if sceneobject in trackobject.is_mipmap else '0'
		self.values[3] = '1' if sceneobject in trackobject.is_nolighting else '0'
		self.values[4] = '1' if sceneobject in trackobject.is_skybox else '0'
		self.values[9] = '1' if sceneobject in trackobject.is_collidable else '0'
		self.values[14] = '1' if sceneobject in trackobject.is_shadow else '0'
		if sceneobject in trackobject.is_transparent: self.values[5] = '1'
		elif sceneobject in trackobject.is_doublesided: self.values[5] = '2'
		else: self.values[5] = '0'
		for name, grp in self.is_surf:
			if sceneobject in grp:
				self.values[16] = name
				print 'grp' + name
				break
		return self

# return objects triangle mesh
def get_tri_mesh(object):
	scn = Blender.Scene.GetCurrent()
	try:
		tempobj = Blender.Object.Get('~temp')
	except ValueError:
		tempobj = Blender.Object.New('Mesh', '~temp')
		mesh = Blender.Mesh.New('~temp')
		tempobj.link(mesh)
	scn.objects.link(tempobj)
	edit_mode = Blender.Window.EditMode()
	if edit_mode: Blender.EditMode(False)
	mesh = tempobj.getData(mesh=1)
	mesh.getFromObject(object)
	oldmode = Blender.Mesh.Mode()
	Blender.Mesh.Mode(Blender.Mesh.SelectModes['FACE'])
	mesh.sel = True
	mesh.quadToTriangle(0)
	scn.objects.unlink(tempobj)
	Blender.Mesh.Mode(oldmode)
	if edit_mode: Blender.Window.EditMode(edit_mode)
	return mesh

# helper class to filter duplicates
class indexed_set(object):
	def __init__(self):
		self.map = {}
		self.list = []
	def get(self, ob):
		fixed = tuple(round(n, 5) for n in ob) # using float as key in dict
		#print fixed
		if not fixed in self.map:
			ni = len(self.list)
			self.map[fixed] = ni
			self.list.append(fixed)
		else:
			ni = self.map[fixed]
		return ni

# strip trailing zeroes
def stripz(s):
	n = 0
	while (n < len(s) and ord(s[n]) != 0):
		n = n + 1
	return s[0:n]

# fill trailing zeroes
def fillz(str, strlen):
	return str + chr(0)*(strlen - len(str))

# load image
def load_image(filename):
	if Blender.sys.exists(filename):
		try:
			return Blender.Image.Load(filename)
		except:	
			print 'JOE Import, Could not load image: ',  filename
	return None
