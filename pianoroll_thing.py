import pygame, sys
import numpy as np
import random

surfarray = pygame.surfarray

size_w = 1300
size_h = 700

pygame.init()
screen = pygame.display.set_mode((size_w, size_h))
pygame.display.set_caption("Hello World")

pianoroll_bg_1_e = [27, 27, 27]
pianoroll_bg_1_o = [33, 33, 33]
pianoroll_bg_2_e = pianoroll_bg_1_o
pianoroll_bg_2_o = pianoroll_bg_1_e

pianoroll_bg_bor_v = pianoroll_bg_1_e
pianoroll_bg_bor_h_bar = [3, 3, 3]
pianoroll_bg_bor_h_non = [18, 18, 18]

border_c_note = [222, 222, 222]


sbr_notelist = np.dtype([
	('used', '<I'), 
	('pos', '<I'), 
	('dur', '<I'), 
	('key', '<I'), 
	('selected', '<B'), 
	])

def gen_float_range(start,stop,step):
	istop = int((stop-start) // step)
	for i in range(int(istop)):
		yield start + i * step

class notelist_store:
	def __init__(self):
		self.notes_data = np.zeros(32, dtype=sbr_notelist)

	def get_used(self):
		return self.notes_data[np.where(self.notes_data['used'])]

	def get_unused(self):
		return np.where(self.notes_data['used']==0)

	def get_first_unused(self):
		wheredata = np.where(self.notes_data['used']==0)[0]
		if len(wheredata): 
			#print('get_first_unused', wheredata[0])
			return wheredata[0]
		return -1

	def add(self, pos, dur, key):
		firstwhere = self.get_first_unused()
		if firstwhere!=-1:
			self.notes_data['used'][firstwhere] = 1
			self.notes_data['pos'][firstwhere] = pos
			self.notes_data['dur'][firstwhere] = dur
			self.notes_data['key'][firstwhere] = key
			self.needs_update = True
			#print('note add ok', self.notes_data)
		return firstwhere

class drewthing:
	def __init__(self, size_w, size_h):
		self.pixels_bg = np.zeros([size_w, size_h, 3], dtype=np.uint8)
		self.pixels_active = np.zeros([size_w, size_h, 3], dtype=np.uint8)
		self.size_w = size_w
		self.size_h = size_h
		self.needs_update = True
		self.notes_store = notelist_store()
		self.notes_data = self.notes_store.notes_data

		self.notelist_snap_dur_on = True
		self.notelist_snap_pos_on = True
		self.notelist_snap_dur = 4
		self.edge_size = 20

		self.cur_state = [0]

	def get_needs_update(self):
		if self.needs_update:
			self.needs_update = False
			return True
		else:
			return False

	def setup_bg(self, zoom_w, zoom_h, timesig_bar):
		self.zoom_w = zoom_w
		self.zoom_h = zoom_h
		self.timesig_bar = timesig_bar

		for x in range((self.size_h//self.zoom_w)+1):
			gridv_s = x*self.zoom_w
			gridv_e = gridv_s+self.zoom_w
			n = (11-x)+((x//12)*12)
			if n>4: self.pixels_bg[:,gridv_s:gridv_e] = pianoroll_bg_1_e if x%2 else pianoroll_bg_1_o
			else: self.pixels_bg[:,gridv_s:gridv_e] = pianoroll_bg_2_e if x%2 else pianoroll_bg_2_o
			if n in [4, 11]: self.pixels_bg[:,gridv_s] = pianoroll_bg_bor_v
		
		for x in range((self.size_w//self.zoom_h)+1):
			self.pixels_bg[x*self.zoom_h,:] = pianoroll_bg_bor_h_non if x%self.timesig_bar else pianoroll_bg_bor_h_bar

		self.notelist_snap = (self.zoom_h/4)

	def init_active(self):
		self.pixels_active[:] = self.pixels_bg[:]

	def get_key(self, posy):
		return (posy//self.zoom_w)

	def get_key_boxw_cur(self, posy):
		ind = (posy//self.zoom_w)*self.zoom_w
		return ind, self.zoom_w+ind

	def get_key_boxw_key(self, key):
		ind = key*self.zoom_w
		return ind, self.zoom_w+ind

	def gfx__draw_box(self, posx, endx, posy, endy, color, alpha):
		tempbg = np.zeros(self.pixels_active.shape, dtype=np.uint8)
		tempbg[:] = self.pixels_active[:]

		self.pixels_active[posx:endx,posy:endy] = color
		totalp = (min(endy, self.size_h)-posy)-2
		for n in range(totalp):
			oldpixel = self.pixels_active[posx+1:endx-1,posy+1+n]
			#self.pixels_active[posx+1:endx-1,posy+1+n] = self.pixels_active[posx+1:endx-1,posy+1+n]*(1-(n/(totalp*2.0)))
			self.pixels_active[posx+1:endx-1,posy+1+n] = self.pixels_active[posx+1:endx-1,posy+1+n]*0.4

		self.pixels_active[posx:endx,posy:endy] = self.pixels_active[posx:endx,posy:endy]*alpha + tempbg[posx:endx,posy:endy]*(1-alpha)

	def note__draw_box(self, posx, posy, endx, endy, selected):
		self.gfx__draw_box(posx, endx, posy, endy, [255, 255, 0] if not selected else [0, 255, 255], 1)
		#if selected:
		#	self.gfx__draw_box(endx, endx+30, posy, endy, [130, 130, 130], 1)

	def get__hover_notes(self, pos):
		self.needs_update = True
		key = self.get_key(pos[1])

		self.notes_data['selected'][:] = 0
		in_and = self.notes_data['used']==1
		in_and &= self.notes_data['key']==key
		in_and &= self.notes_data['pos']<pos[0]
		in_and &= pos[0]<(self.notes_data['pos']+self.notes_data['dur'])
		return np.where(in_and)[0]

	def check_edges(self, pos, num):
		posh = pos[0]-self.notes_data['pos'][num]
		durh = (self.notes_data['dur'][num]+self.notes_data['pos'][num])-pos[0]
		if self.edge_size>posh:
			return 1
		if self.edge_size>durh:
			return -1
		return 0

	def mouse__movement(self, pos):
		if self.cur_state[0] == 2:
			xpos = pos[0]-self.cur_state[2]
			if self.notelist_snap_pos_on:
				xpos = xpos//self.notelist_snap
				xpos *= self.notelist_snap
			self.notes_data['pos'][self.cur_state[1]] = max(xpos, 0)
			self.notes_data['key'][self.cur_state[1]] = self.get_key(pos[1])
			self.needs_update = True
		if self.cur_state[0] == 3:
			newdur = pos[0]-self.notes_data['pos'][self.cur_state[1]]
			if self.notelist_snap_dur_on:
				newdur = newdur//self.notelist_snap
				newdur *= self.notelist_snap
			newdur = max(newdur, self.notelist_snap)
			self.notes_data['dur'][self.cur_state[1]] = newdur
			self.needs_update = True
			self.prevdur = newdur
		if self.cur_state[0] == 4:
			print('mouse__movement to 4')
			newdur = pos[0]-self.notes_data['pos'][self.cur_state[1]]
			if self.notelist_snap_dur_on:
				newdur = newdur//self.notelist_snap
				newdur *= self.notelist_snap
			newdur = max(newdur, self.notelist_snap)
			self.notes_data['dur'][self.cur_state[1]] = newdur
			self.needs_update = True
			self.prevdur = newdur
		if self.cur_state[0] == 5:
			print('mouse__movement to 5')
			xpos = pos[0]
			if self.notelist_snap_pos_on:
				xpos = xpos//self.notelist_snap
				xpos *= self.notelist_snap
	
			endpos = self.cur_state[2]+self.cur_state[3]

			xpos = max(xpos, 0)
			xpos = min(xpos, endpos-20)
	
			endpos = endpos-xpos
			self.notes_data['pos'][self.cur_state[1]] = max(xpos, 0)
			self.notes_data['dur'][self.cur_state[1]] = endpos
			self.needs_update = True
		pass

	def mouse__down(self, pos):

		wherevals = self.get__hover_notes(pos)
		if len(wherevals): 
			firstwhere = wherevals[-1]
			edgetype = self.check_edges(pos, firstwhere)
			self.notes_data['selected'][firstwhere] = 1
			if edgetype == 0:
				self.cur_state = [2, firstwhere, pos[0]-self.notes_data['pos'][firstwhere]]
				print('cur_state to 2')
			else:
				if edgetype == -1:
					self.cur_state = [4, firstwhere, pos[0]-self.notes_data['pos'][firstwhere], self.notes_data['dur'][firstwhere]]
					print('cur_state to 4')
				if edgetype == 1:
					self.cur_state = [5, firstwhere, self.notes_data['dur'][firstwhere], self.notes_data['pos'][firstwhere]]
					print('cur_state to 5')
	
		elif self.cur_state[0] in [1, 3, 4]:
			self.cur_state = [0]
			print('cur_state to 0')
		elif self.cur_state[0] == 0:
			keydata = drawthing_obj.get_key(pos[1])
			wheredata = self.notes_store.add(pos[0], 57 if not self.notelist_snap_dur_on else self.notelist_snap_dur, keydata)
			if wheredata>=0: 
				self.cur_state = [3, wheredata]
				print('cur_state to 3')
				self.needs_update = True

	def draw__allnotes(self):
		drawthing_obj.init_active()
		for n, x in enumerate(self.notes_store.get_used()):
			if x['used']:
				w_start, w_end = drawthing_obj.get_key_boxw_key(x['key'])
				drawthing_obj.note__draw_box(x['pos'], w_start, x['pos']+x['dur'], w_end, x['selected'])

	def mouse__up(self, pos):
		if self.cur_state[0] in [2]:
			self.cur_state = [1]
			print('cur_state to 1')
		if self.cur_state[0] in [3, 4, 5]:
			self.cur_state = [0]
			print('cur_state to 0')


drawthing_obj = drewthing(size_w, size_h)
drawthing_obj.setup_bg(12, 22, 4)
drawthing_obj.init_active()


drawthing_obj.needs_update = True


while True:
	for event in pygame.event.get():
		if event.type == pygame.QUIT:
			pygame.quit()
			sys.exit()
		if event.type == pygame.MOUSEBUTTONDOWN:
			pos=pygame.mouse.get_pos()
			#print ("DOWN x = {}, y = {}".format(pos[0], pos[1]))
			drawthing_obj.mouse__down(pos)
		if event.type == pygame.MOUSEBUTTONUP:
			pos=pygame.mouse.get_pos()
			#print ("UP x = {}, y = {}".format(pos[0], pos[1]))
			drawthing_obj.mouse__up(pos)
		if event.type == pygame.MOUSEMOTION:
			pos=pygame.mouse.get_pos()
			drawthing_obj.mouse__movement(pos)

	if drawthing_obj.get_needs_update():
		#print('update')
		drawthing_obj.draw__allnotes()
		surfarray.blit_array(screen, drawthing_obj.pixels_active )
		pygame.display.flip()