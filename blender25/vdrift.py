# ***** BEGIN GPL LICENSE BLOCK *****
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
# ***** END GPL LICENCE BLOCK *****

bl_info = {
	'name': 'VDrfit JOE format',
	'description': 'Import-Export to VDrift JOE files (.joe)',
	'author': 'NaN, port of VDrift blender24 scripts',
	'version': (0, 6),
	'blender': (2, 5, 8),
	'api': 35622,
	'location': 'File > Import-Export',
	'warning': '',
	'wiki_url': 'http://', 
	'tracker_url': 'http://',
	'category': 'Import-Export'}

import bpy
from bpy.props import StringProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper
from bpy_extras.image_utils import load_image
from struct import Struct

class joe_vertex:
	bstruct = Struct('<fff')
	
	# read list of 3-tuples
	@staticmethod
	def read(num, file):
		values = []
		for i in range(num):
			data = file.read(joe_vertex.bstruct.size)
			v = joe_vertex.bstruct.unpack(data)
			values.append(v)
		return values
	
	# write a list of 3-tuples
	@staticmethod
	def write(values, file):
		for v in values:
			data = joe_vertex.bstruct.pack(v[0], v[1], v[2])
			file.write(data)

class joe_texcoord:
	bstruct = Struct('<ff')
	
	# read a list of 2-tuples
	@staticmethod
	def read(num, file):
		values = []
		for i in range(num):
			data = file.read(joe_texcoord.bstruct.size)
			v = joe_texcoord.bstruct.unpack(data)
			values.append((v[0], 1 - v[1]))
		return values
	
	# write a list of 2-tuples
	@staticmethod
	def write(values, file):
		for v in values:
			data = joe_texcoord.bstruct.pack(v[0], 1 - v[1])
			file.write(data)

class joe_face:
	__slots__ = 'vertex_index', 'normal_index', 'texture_index'
	bstruct = Struct('<3h3h3h')
   
	def __init__(self):
		self.vertex_index = [0, 0, 0]
		self.normal_index = [0, 0, 0]
		self.texture_index = [0, 0, 0]
	
	def load (self, file):
		data = file.read(joe_face.bstruct.size)
		v = joe_face.bstruct.unpack(data)
		self.vertex_index = [v[0], v[1], v[2]]
		self.normal_index = [v[3], v[4], v[5]]
		self.texture_index = [v[6], v[7], v[8]]
		return self
	
	def save(self, file):
		data = joe_face.bstruct.pack(self.vertex_index[0],self.vertex_index[1],self.vertex_index[2],
			self.normal_index[0],self.normal_index[1],self.normal_index[2],
			self.texture_index[0],self.texture_index[1],self.texture_index[2])
		file.write(data)

class joe_frame:
	__slots__ = 'num_vertices', 'num_normals', 'num_texcoords',\
				'faces', 'verts', 'texcoords', 'normals'
	bstruct = Struct("<3i")

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
		data = file.read(joe_frame.bstruct.size)
		v = joe_frame.bstruct.unpack(data)
		self.num_vertices = v[0]
		self.num_texcoords = v[1]
		self.num_normals = v[2]
		# mesh data
		self.verts = joe_vertex.read(self.num_vertices, file)
		self.normals = joe_vertex.read(self.num_normals, file)
		self.texcoords = joe_texcoord.read(self.num_texcoords, file)
		return self
	
	def save(self, file):
		# header
		data = joe_frame.bstruct.pack(self.num_vertices, self.num_texcoords, self.num_normals)
		file.write(data)
		# mesh data
		joe_vertex.write(self.verts, file)
		joe_vertex.write(self.normals, file)
		joe_texcoord.write(self.texcoords, file)
	
	def from_mesh(self, obj):
		mesh = util.get_tri_mesh(obj)
		mesh.transform(obj.matrix_world)
		normals = util.indexed_set()
		vertices = util.indexed_set()
		texcoords = util.indexed_set()
		# get vertices and normals
		for f in mesh.faces:
			jf = joe_face()
			jf.vertex_index = [vertices.get(mesh.vertices[vi].co) for vi in f.vertices]
			if f.use_smooth:
				jf.normal_index = [normals.get(mesh.vertices[vi].normal) for vi in f.vertices]
			else:
				jf.normal_index = [normals.get(f.normal)] * 3
			self.faces.append(jf)
		# get texture coordinates
		if len(mesh.uv_textures) != 0:
			for i, f in enumerate(self.faces):
				mf = mesh.uv_textures[0].data[i]
				f.texture_index = [texcoords.get((uv[0], uv[1])) for uv in mf.uv[0:3]]
		self.normals = normals.list
		self.verts = vertices.list
		self.texcoords = texcoords.list
		self.num_normals = len(self.normals)
		self.num_texcoords = len(self.texcoords)
		self.num_vertices = len(self.verts)
		return self

	# remove faces consisting less then 3 vertices
	def remove_degenerate_faces(self):
		faces = []
		for f in self.faces:
			vi = f.vertex_index
			if vi[0] != vi[1] and vi[1] != vi[2] and vi[0] != vi[2]:
				faces.append(f)
		self.faces = faces

	# blender only supports one normal per vertex
	def duplicate_verts_with_multiple_normals(self):
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
	
	# in blender 2.5 the last vertex index shall not be 0 
	def swizzle_face_vertices(self):
		for f in self.faces:
			vi = f.vertex_index
			ni = f.normal_index
			ti = f.texture_index
			if vi[2] == 0:
				vi[0], vi[1], vi[2] = vi[2], vi[0], vi[1]
				ni[0], ni[1], ni[2] = ni[2], ni[0], ni[1]
				ti[0], ti[1], ti[2] = ti[2], ti[0], ti[1]
	
	def to_mesh(self, name, image):
		# cleanup joe
		self.remove_degenerate_faces()
		self.swizzle_face_vertices()
		self.duplicate_verts_with_multiple_normals()
		
		# new mesh
		mesh = bpy.data.meshes.new(name)
		mesh.vertices.add(len(self.verts))
		mesh.faces.add(len(self.faces))
		
		# set vertices
		for i, v in enumerate(self.verts):
			mesh.vertices[i].co = v
		for f in self.faces:
			for i in range(3):
				mesh.vertices[f.vertex_index[i]].normal = self.normals[f.normal_index[i]]
		
		# set faces
		for i, f in enumerate(self.faces):
			mesh.faces[i].vertices = (f.vertex_index[0], f.vertex_index[1], f.vertex_index[2], 0)
			mesh.faces[i].use_smooth = True
		
		# set texture coordinates
		mesh.uv_textures.new()
		for i, f in enumerate(self.faces):
			mf = mesh.uv_textures[0].data[i]
			mf.uv1 = self.texcoords[f.texture_index[0]]
			mf.uv2 = self.texcoords[f.texture_index[1]]
			mf.uv3 = self.texcoords[f.texture_index[2]]
			if (image):
				mf.image = image
				mf.use_image = True
		
		mesh.validate()
		mesh.update()
		return bpy.data.objects.new(name, mesh)

class joe_obj:
	__slots__ = 'ident', 'version', 'num_faces', 'num_frames', 'frames'
	bstruct = Struct("<4i")
	
	def __init__(self):
		self.ident = 844121161
		self.version = 3
		self.num_faces = 0
		self.num_frames = 0
		self.frames = []
   
	def load(self, file):
		# header
		data = file.read(joe_obj.bstruct.size)
		v = joe_obj.bstruct.unpack(data)
		self.ident = v[0]
		self.version = v[1]
		self.num_faces = v[2]
		self.num_frames = v[3]
		# frames
		for i in range(self.num_frames):
			self.frames.append(joe_frame())
			for j in range(self.num_faces):
				self.frames[i].faces.append(joe_face().load(file))
			self.frames[i].load(file)
		return self
	
	def save(self, file):
		# header
		data = joe_obj.bstruct.pack(self.ident, self.version, self.num_faces, self.num_frames)
		file.write(data)
		# frames
		for i in range(self.num_frames):
			for j in range(self.num_faces):
				self.frames[i].faces[j].save(file)
			self.frames[i].save(file)
			
	def to_mesh(self, name, image, num_frames=1):
		frames = []
		for i in range(num_frames):
			bpy.context.scene.frame_set(i)
			frames.append(self.frames[i].to_mesh(name, image))
		return frames[0]
		
	def from_mesh(self, mesh_obj, num_frames=1):
		for i in range(num_frames):
			bpy.context.scene.frame_set(i)
			frame = joe_frame()
			frame.from_mesh(mesh_obj)
			self.frames.append(frame)
		self.num_frames = num_frames
		self.num_faces = len(self.frames[0].faces)
		return self
'''
class joe_pack:
	versionstr = 'JPK01.00'
	binary_format = '<2i'  #little-endian (<), 2 integers (2i)
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
			fat.append((offset, length, util.stripz(name)))
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
			name = util.fillz('', self.maxstrlen)
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
			name = util.fillz(name, self.maxstrlen)
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
				self.images[imagename] = util.load_image(path)

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
'''
class util:
	# helper class to filter duplicates
	class indexed_set(object):
		def __init__(self):
			self.map = {}
			self.list = []
		def get(self, ob):
			# using float as key in dict
			fixed = tuple(round(n, 5) for n in ob)
			if not fixed in self.map:
				ni = len(self.list)
				self.map[fixed] = ni
				self.list.append(fixed)
			else:
				ni = self.map[fixed]
			return ni

	# strip trailing zeroes
	@staticmethod
	def stripz(s):
		n = 0
		while (n < len(s) and ord(s[n]) != 0):
			n = n + 1
		return s[0:n]

	# fill trailing zeroes
	@staticmethod
	def fillz(str, strlen):
		return str + chr(0)*(strlen - len(str))

	@staticmethod
	def delete_object(object):
		bpy.context.scene.objects.unlink(object)
		bpy.data.objects.remove(object)

	@staticmethod
	def duplicate_object(object, name):
		# save current selection
		selected_objects = bpy.context.selected_objects[:]
		active_object = bpy.context.active_object
		bpy.ops.object.select_all(action = 'DESELECT')
		
		# copy object
		object.select = True
		bpy.ops.object.duplicate()
		object_duplicate = bpy.context.selected_objects[0]
		object_duplicate.name = name
		
		# reset selection
		bpy.context.scene.objects.active = active_object
		for obj in selected_objects: obj.select = True
		return object_duplicate
		
	@staticmethod
	def convert_to_tris(object):
		mesh = object.data
		bpy.context.scene.objects.active = object
		bpy.ops.object.mode_set(mode = 'EDIT', toggle = False)
		bpy.ops.mesh.select_all(action = 'SELECT')
		bpy.ops.mesh.quads_convert_to_tris()
		bpy.ops.object.mode_set(mode = 'OBJECT', toggle = False)
		return mesh

	@staticmethod
	def get_tri_mesh(object):
		quad = False
		mesh = object.data
		for face in mesh.faces:
			if len(face.vertices) == 4:
				quad = True
				break
		if quad:
			object = util.duplicate_object(object, '~joetmp')
			mesh = util.convert_to_tris(object)
			util.delete_object(object)
		return mesh

class export_joe(bpy.types.Operator, ExportHelper):
	bl_idname = 'export.joe'
	bl_label = 'Export JOE'
	filename_ext = '.joe'
	filter_glob = StringProperty(
			default='*.joe',
			options={'HIDDEN'})
	
	def __init__(self):
		try:
			self.object = bpy.context.selected_objects[0]
		except:
			self.object = None
		#bpy.ops.object.mode_set(mode='OBJECT', toggle = False)
	
	def execute(self, context):
		props = self.properties
		filepath = self.filepath
		filepath = bpy.path.ensure_ext(filepath, self.filename_ext)
		
		if len(bpy.context.selected_objects[:]) == 0:
			raise NameError('Please select one object!')
		
		if len(bpy.context.selected_objects[:]) > 1:
			raise NameError('Please select a single object!')
		
		object = self.object
		if object.type != 'MESH':
			raise NameError('Selected object must be a mesh!')
			
		try:
			file = open(filepath, 'wb')
			joe = joe_obj().from_mesh(object)
			joe.save(file)
			file.close()
		finally:
			self.report({'INFO'},  object.name + ' exported')
		
		return {'FINISHED'}
		
	def invoke(self, context, event):
		context.window_manager.fileselect_add(self);
		return {'RUNNING_MODAL'}

class import_joe(bpy.types.Operator, ImportHelper):
	bl_idname = 'import.joe'
	bl_label = 'Import JOE'
	filename_ext = '.joe'
	filter_glob = StringProperty(
		default='*.joe',
		options={'HIDDEN'})
	
	def execute(self, context):
		props = self.properties
		filepath = bpy.path.ensure_ext(self.filepath, self.filename_ext)
		try:
			image = None #load_image(filepath_img)
			file = open(filepath, 'rb')
			joe = joe_obj().load(file)
			file.close()
			object = joe.to_mesh(bpy.path.basename(filepath), image)
			context.scene.objects.link(object)
		finally:
			self.report({'INFO'},  filepath + ' imported')
		return {'FINISHED'}

def menu_export_joe(self, context):
	self.layout.operator(export_joe.bl_idname, text = 'VDrift JOE (.joe)')
	
def menu_import_joe(self, context):
	self.layout.operator(import_joe.bl_idname, text = 'VDrift JOE (.joe)')
 
def register():
	bpy.utils.register_module(__name__)
	bpy.types.INFO_MT_file_export.append(menu_export_joe)
	bpy.types.INFO_MT_file_import.append(menu_import_joe)
 
def unregister():
	bpy.utils.unregister_module(__name__)
	bpy.types.INFO_MT_file_export.remove(menu_export_joe)
	bpy.types.INFO_MT_file_import.remove(menu_import_joe)
 
if __name__ == '__main__':
	register()