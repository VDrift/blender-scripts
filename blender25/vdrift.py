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
	'name': 'VDrift JOE/JPK format',
	'description': 'Import-Export to VDrift JOE and JPK files (.joe, .jpk)',
	'author': 'NaN, port of VDrift blender24 scripts',
	'version': (0, 7),
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
from os import path

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
		data = joe_face.bstruct.pack(
			self.vertex_index[0],self.vertex_index[1],self.vertex_index[2],
			self.normal_index[0],self.normal_index[1],self.normal_index[2],
			self.texture_index[0],self.texture_index[1],self.texture_index[2])
		file.write(data)


class joe_frame:
	__slots__ = 'num_vertices', 'num_normals', 'num_texcoords',\
				'faces', 'verts', 'texcoords', 'normals'
	bstruct = Struct('<3i')

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
		object = bpy.data.objects.new(name, mesh)
		bpy.context.scene.objects.link(object)
		return object

class joe_obj:
	__slots__ = 'ident', 'version', 'num_faces', 'num_frames', 'frames'
	bstruct = Struct('<4i')
	
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


class joe_pack:
	versionstr = 'JPK01.00'
	bstruct = Struct('<2i')
	
	def __init__(self):
		self.numobjs = 0
		self.maxstrlen = 0
		self.joe = {}
		self.list = {}
		self.images = {}
		self.surfaces = []
			
	def load(self, filename):
		from time import clock
		# don't change call order
		t0 = clock()
		self.load_list(filename)
		t1 = clock()
		print('load list: ' + str(t1 - t0))
		t0 = t1
		self.load_images(filename)
		t1 = clock()
		print('load images: ' + str(t1 - t0))
		t0 = t1
		self.load_jpk(filename)
		t1 = clock()
		print('load jpk: ' + str(t1 - t0))
		return self
	
	def save(self, filename):
		from time import clock
		t0 = clock()
		self.save_jpk(filename)
		t1 = clock()
		print('save jpk: ' + str(t1 - t0))
		t0 = t1
		self.save_list(filename)
		t1 = clock()
		print('save list: ' + str(t1 - t0))
		
	def to_mesh(self):
		trackobject.create_groups()
		for name, joe in self.joe.items():
			image = None
			trackobj = self.list.get(name)
			if trackobj:
				imagename = trackobj.values[1]
				image = self.images[imagename]
				obj = joe.to_mesh(name, image)
				trackobj.to_obj(obj)
			else:
				print(name + ' not imported. Not in list.txt.')
		
	def from_mesh(self):
		objlist = bpy.context.scene.objects
		trackobject.set_groups()
		for obj in objlist:
			if obj.type != 'MESH':
				continue
			if obj.name.startswith('~'):
				continue
			if len(obj.data.faces) == 0:
				print(obj.name + ' not exported. No faces.')
				continue
			if len(obj.data.uv_textures) == 0:
				print(obj.name + ' not exported. No texture coordinates.')
				continue
			if obj.data.uv_textures[0].data[0].image == None:
				print(obj.name + ' not exported. No texture assigned.')
				continue
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
		self.numobjs = len(self.joe)
		return self
		
	def load_jpk(self, filename):
		file = open(filename, 'rb')
		# header
		version = file.read(len(joe_pack.versionstr))
		data = file.read(joe_pack.bstruct.size)
		v = joe_pack.bstruct.unpack(data)
		self.numobjs = v[0]
		self.maxstrlen = v[1]
		# fat
		fat = []
		for i in range(self.numobjs):
			data = file.read(joe_pack.bstruct.size)
			v = joe_pack.bstruct.unpack(data)
			offset = v[0]
			length = v[1]
			data = file.read(self.maxstrlen)
			# strip trailing zeros
			for i in range(self.maxstrlen):
				if data[i] == 0:
					data = data[:i]
					break
			name = data.decode('ascii')
			fat.append((offset, length, name))
		# data
		for offset, length, name in fat:
			pos = file.tell()
			delta = offset - pos
			if delta < 0:
				print('Error reading: ', name, offset)
				return
			elif delta > 0:
				file.read(delta)
			joe = joe_obj().load(file)
			self.joe[name] = joe
		file.close()
	
	def save_jpk(self, filename):
		try:
			file = open(filename, 'rb+')
		except IOError:
			file = open(filename, 'wb')
		# header
		file.write(self.versionstr.encode('ascii'))
		data = joe_pack.bstruct.pack(self.numobjs, self.maxstrlen)
		file.write(data)
		# allocate fat
		fat_offset = file.tell()
		for i in range(self.numobjs):
			data = joe_pack.bstruct.pack(0, 0)
			file.write(data)
			name = util.fillz('', self.maxstrlen)
			file.write(name.encode('ascii'))
		# write data / build fat
		fat = []
		for name, joe in self.joe.items():
			offset = file.tell()
			joe.save(file)
			length = file.tell() - offset
			fat.append((offset, length, name))
		# fill fat
		file.seek(fat_offset)
		for offset, length, name in fat:
			data = joe_pack.bstruct.pack(offset, length)
			file.write(data)
			name = util.fillz(name, self.maxstrlen)
			file.write(name.encode('ascii'))
		file.close()
		
	def load_list(self, filename):
		dir = path.dirname(filename)
		list_path = path.join(dir, 'list.txt')
		try:
			list_file = open(list_path)
		except IOError:
			print(list_path + ' not found.')
			return
		# read objects
		line = list_file.readline()
		while line != '':
			if '.joe' in line:
				object = trackobject()
				name = line.strip()
				line = object.read(name, list_file)
				self.list[object.values[0]] = object
			else:
				line = list_file.readline()
		if len(self.list) == 0:
			print('Failed to load list.txt.')
		list_file.close()
		
	def save_list(self, filename):
		dir = path.dirname(filename)
		list_path = path.join(dir, 'list.txt')
		file = open(list_path, 'w')
		file.write('17\n\n')
		i = 0
		for name, object in self.list.items():
			file.write('#entry ' + str(i) + '\n')
			object.write(file)
			i = i + 1
		file.close()
		
	def load_images(self, filename):
		dir = path.dirname(filename)
		for name, object in self.list.items():
			imagename = object.values[1]
			if imagename not in self.images:
				imagepath = path.join(dir, imagename)
				self.images[imagename] = load_image(imagepath)

class trackobject:
	names = ('model', 'texture', 'mipmap', 'lighting', 'skybox', 'blend',\
			'bump length', 'bump amplitude', 'drivable', 'collidable',\
			'non treaded', 'treaded', 'roll resistance', 'roll drag',\
			'shadow', 'clamp', 'surface')
	namemap = dict(zip(names, range(17)))
	
	@staticmethod	
	def create_groups():
		trackobject.grp_surf = []
		trackobject.grp = {}
		for name in ('mipmap', 'nolighting', 'skybox', 'transparent',\
					'doublesided', 'collidable', 'shadow', 'clampu', 'clampv'):
			grp = bpy.data.groups.get(name)
			if grp == None:
				grp = bpy.data.groups.new(name)
			trackobject.grp[name] = grp.objects
	
	@staticmethod
	def set_groups():
		trackobject.create_groups()
		trackobject.is_surf = []
		for grp in bpy.data.groups:
			if grp.name == 'mipmap':
				trackobject.is_mipmap = set(grp.objects)
			elif grp.name == 'nolighting':
				trackobject.is_nolighting = set(grp.objects)
			elif grp.name == 'skybox':
				trackobject.is_skybox = set(grp.objects)
			elif grp.name == 'transparent':
				trackobject.is_transparent = set(grp.objects)
			elif grp.name == 'doublesided':
				trackobject.is_doublesided = set(grp.objects)
			elif grp.name == 'collidable':
				trackobject.is_collidable = set(grp.objects)
			elif grp.name == 'shadow':
				trackobject.is_shadow = set(grp.objects)
			elif grp.name == 'clampu':
				trackobject.is_clampu = set(grp.objects)
			elif grp.name == 'clampv':
				trackobject.is_clampv = set(grp.objects)
			elif grp.name.startswith('surface'):
				trackobject.is_surf.append((grp.name.split('-')[-1], set(grp.objects)))
	
	def __init__(self):
		self.values = ['none', 'none', '1', '0', '0', '0',\
						'1.0', '0.0', '0', '0',\
						'1.0', '0.9', '1.0', '0.0',\
						'0', '0', '0']
	
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
	
	def to_obj(self, object):
		object['model'] = self.values[0]
		object['texture'] = self.values[1]
		if self.values[2] == '1': trackobject.grp['mipmap'].link(object)
		if self.values[3] == '1': trackobject.grp['nolighting'].link(object)
		if self.values[4] == '1': trackobject.grp['skybox'].link(object)
		if self.values[5] == '1': trackobject.grp['transparent'].link(object)
		if self.values[5] == '2': trackobject.grp['doublesided'].link(object)
		if self.values[8] == '1' or self.values[9] == '1': trackobject.grp['collidable'].link(object)
		if self.values[14] == '1': trackobject.grp['shadow'].link(object)
		if self.values[15] == '1' or self.values[15] == '3': trackobject.grp['clampu'].link(object)
		if self.values[15] == '2' or self.values[15] == '3': trackobject.grp['clampv'].link(object)
		surfid = int(self.values[16])
		while surfid >= len(trackobject.grp_surf):
			surfnum = len(trackobject.grp_surf)
			surfname = 'surface-'+str(surfnum)
			grp = bpy.data.groups.get(surfname)
			if grp == None:
				grp = bpy.data.groups.new(surfname)
			trackobject.grp_surf.append(grp.objects)
		trackobject.grp_surf[surfid].link(object)
		return self
	
	# set from object
	def from_obj(self, object):
		self.values[0] = object.get('model', object.name)
		self.values[1] = object.get('texture', object.data.uv_textures[0].data[0].image.name)
		self.values[2] = '1' if object in trackobject.is_mipmap else '0'
		self.values[3] = '1' if object in trackobject.is_nolighting else '0'
		self.values[4] = '1' if object in trackobject.is_skybox else '0'
		if object in trackobject.is_transparent: self.values[5] = '1'
		elif object in trackobject.is_doublesided: self.values[5] = '2'
		else: self.values[5] = '0'
		self.values[9] = '1' if object in trackobject.is_collidable else '0'
		self.values[14] = '1' if object in trackobject.is_shadow else '0'
		self.values[15] = '1' if object in trackobject.is_clampu else '0'
		if object in trackobject.is_clampv:
			self.values[15] = '2' if self.values[15] == '0' else '3'
		for name, grp in self.is_surf:
			if object in grp:
				self.values[16] = name
				break
		return self

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
	
	def execute(self, context):
		props = self.properties
		filepath = bpy.path.ensure_ext(self.filepath, self.filename_ext)
		
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
			joe.to_mesh(bpy.path.basename(filepath), image)
			file.close()
		finally:
			self.report({'INFO'},  filepath + ' imported')
		return {'FINISHED'}


class export_jpk(bpy.types.Operator, ExportHelper):
	bl_idname = 'export.jpk'
	bl_label = 'Export JPK'
	filename_ext = '.jpk'
	filter_glob = StringProperty(
			default='*.jpk',
			options={'HIDDEN'})
	
	def execute(self, context):
		props = self.properties
		filepath = bpy.path.ensure_ext(self.filepath, self.filename_ext)
		try:
			jpk = joe_pack().from_mesh()
			jpk.save(filepath)
		finally:
			self.report({'INFO'},  filepath + ' exported')
		
		return {'FINISHED'}
		
	def invoke(self, context, event):
		context.window_manager.fileselect_add(self);
		return {'RUNNING_MODAL'}


class import_jpk(bpy.types.Operator, ImportHelper):
	bl_idname = 'import.jpk'
	bl_label = 'Import JPK'
	filename_ext = '.jpk'
	filter_glob = StringProperty(
		default='*.jpk',
		options={'HIDDEN'})
	
	def execute(self, context):
		props = self.properties
		filepath = bpy.path.ensure_ext(self.filepath, self.filename_ext)
		try:
			jpk = joe_pack().load(filepath)
			jpk.to_mesh()
		finally:
			self.report({'INFO'},  filepath + ' imported')
		return {'FINISHED'}

def menu_export_joe(self, context):
	self.layout.operator(export_joe.bl_idname, text = 'VDrift JOE (.joe)')


def menu_import_joe(self, context):
	self.layout.operator(import_joe.bl_idname, text = 'VDrift JOE (.joe)')


def menu_export_jpk(self, context):
	self.layout.operator(export_jpk.bl_idname, text = 'VDrift JPK (.jpk)')


def menu_import_jpk(self, context):
	self.layout.operator(import_jpk.bl_idname, text = 'VDrift JPK (.jpk)')


def register():
	bpy.utils.register_module(__name__)
	bpy.types.INFO_MT_file_export.append(menu_export_joe)
	bpy.types.INFO_MT_file_import.append(menu_import_joe)
	bpy.types.INFO_MT_file_export.append(menu_export_jpk)
	bpy.types.INFO_MT_file_import.append(menu_import_jpk)


def unregister():
	bpy.utils.unregister_module(__name__)
	bpy.types.INFO_MT_file_export.remove(menu_export_joe)
	bpy.types.INFO_MT_file_import.remove(menu_import_joe)
	bpy.types.INFO_MT_file_export.remove(menu_export_jpk)
	bpy.types.INFO_MT_file_import.remove(menu_import_jpk)


if __name__ == '__main__':
	register()