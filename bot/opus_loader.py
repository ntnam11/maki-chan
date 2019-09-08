import platform
import shutil

from discord import opus

OPUS_LIBS = ['libopus-0.x86.dll', 'libopus-0.x64.dll', 'libopus-0.dll', 'libopus.so.0', 'libopus.0.dylib']
OPUS_LIBS_LINUX = ['libopus.so', 'libopus.so.0.6.1', 'libopus.so.0', 'libGL.so.1', 'libopus.so.1']

def load_opus_lib(opus_libs=OPUS_LIBS):
	if platform.system() == 'Linux':
		print("Linux detected")

		try:
			shutil.copy("./.apt/lib/x86_64-linux-gnu/libusb-1.0.so.0", "./.apt/usr/lib/x86_64-linux-gnu/libusb-1.0.so.0")
			shutil.copy("./.apt/usr/lib/x86_64-linux-gnu/pulseaudio/libpulsecommon-11.1.so", "./.apt/usr/lib/x86_64-linux-gnu/libpulsecommon-11.1.so")
			shutil.copy("./.apt/lib/x86_64-linux-gnu/libslang.so.2", "./.apt/usr/lib/x86_64-linux-gnu/libslang.so.2")
		except FileNotFoundError:
			pass

		for opus_lib in OPUS_LIBS_LINUX:
			try:
				opus.load_opus(opus_lib)
				print("Tried %s" % opus_lib)
				return
			except OSError:
				raise RuntimeError('Could not load an opus lib. Tried %s' % (', '.join(opus_libs)))

	if opus.is_loaded():
		print('Opus loaded')
		return True
		
	# else:
	# 	for opus_lib in opus_libs:
	# 		try:
	# 			opus.load_opus(opus_lib)
	# 			print("Tried %s" % opus_lib)
	# 			return
	# 		except OSError:
	# 			raise RuntimeError('Could not load an opus lib. Tried %s' % (', '.join(opus_libs)))
