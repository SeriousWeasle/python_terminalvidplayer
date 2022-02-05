from playsound import playsound #needed to play sound for video
import moviepy.editor as mp #used for extracting audio track
from PIL import Image #used for image processing
import sys, cv2, os, math, time, curses #curses #sys is used for argument processing and curses for drawing in the terminal, os for terminal size, math for math
from pathlib import Path #used for file paths
from tqdm import tqdm #progress bars
from threading import Timer, Thread #timer for making frames draw in correct time

#define all paths to specific folders
PROG_DIR = Path(__file__).parent
AUDIO_DIR = PROG_DIR / 'extract/audio'
UNPROC_FRAME_DIR = PROG_DIR / 'extract/frames_fullsize'
PROC_FRAME_DIR = PROG_DIR / 'extract/frames_ascii'

CHAR_ASPECT = 0.5 #a character is half as wide as it is tall in the windows command line

ASCII_SYMBOLS_USABLE = ["B", "S", "#", "&", "@", "$", "%", "*", "!", ".", " "]

Vid_frames = 0
Vid_framerate = 0

Vid_width = 0
Vid_height = 0

Term_width = 0
Term_height = 0

Char_width = 0
Char_height = 0

Output_width = 0
Output_height = 0

Playback_index = 0

stdscr = None
refresh = None

#this function stores the audio under ./extract/audio/sndfile.mp3
def ExtractAudioTrack(fileName : str):
    vidClip = mp.VideoFileClip(str(PROG_DIR / fileName)) #open clip in moviePy
    vidClip.audio.write_audiofile(r"%s" % str(AUDIO_DIR / "sndfile.mp3")) #save audio track

def ExtractVideoFrames(fileName : str):
    videoCap = cv2.VideoCapture(fileName) #open video file with cv2
    global Vid_frames
    global Vid_height
    global Vid_width
    global Vid_framerate
    Vid_frames = int(videoCap.get(cv2.CAP_PROP_FRAME_COUNT)) #get frame count and make globally available

    Vid_height = int(videoCap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    Vid_width = int(videoCap.get(cv2.CAP_PROP_FRAME_WIDTH))

    Vid_framerate = int(videoCap.get(cv2.CAP_PROP_FPS))
    print(Vid_framerate)
    success, img = videoCap.read()
    for i in tqdm(range(Vid_frames), desc="Extracting frames"): #get all video frames and save them
        cv2.imwrite(str(UNPROC_FRAME_DIR / f"{i}.png"), img)
        success, img = videoCap.read() #read next frame

def DetermineAspect():
    global Vid_width
    global Vid_height
    vid_aspect = Vid_width / Vid_height #get video aspect ratio

    global Output_height
    global Output_width
    global Char_height
    global Char_width

    print("Do not resize terminal")
    Term_width = os.get_terminal_size().columns
    Term_height = os.get_terminal_size().lines

    unRoundedWidth = min(Term_width, (Term_height / CHAR_ASPECT) * vid_aspect) #use the smallest of the 2, either height converted to width or just the width
    unRoundedHeight = (unRoundedWidth / vid_aspect) * CHAR_ASPECT #calculate the height

    #floor both values, makes sure that the image is not too big for the terminal
    Output_height = math.floor(unRoundedHeight)
    Output_width = math.floor(unRoundedWidth)

    #calculate the size of a character in pixels for the terminal, overshooting is ok
    Char_height = math.ceil(Vid_height / Output_height)
    Char_width = math.ceil(Vid_width / Output_width)

    #print all values for debugging purposes
    print(f"Video size: {Vid_width}, {Vid_height}")
    print(f"Terminal viewport size: {Output_width}, {Output_height}")
    print(f"Pixels per character: {Char_width}, {Char_height}")

def Determine_Char(lx:int, hx:int, ly:int, hy:int, img:Image):
    pixels = img.load()
    value = 0
    for x in range(lx, hx):
        for y in range(ly, hy):
            value += int(pixels[x, y])
    area = (hx - lx) * (hy - ly)
    value = round(((value / area) / 255) * 10)
    return ASCII_SYMBOLS_USABLE[value]

def ASCIIFy():
    global Term_height
    global Term_width

    global Char_width
    global Char_height

    global Vid_width
    global Vid_height

    global Output_width
    global Output_height

    for i in tqdm(range(Vid_frames), desc="ASCII-fying frames"): #go over all frames
        frame = Image.open(str(UNPROC_FRAME_DIR / f"{i}.png")) #open them
        frame = frame.convert("L") #grayscale, lossless
        output = ""
        #loop over all blocks in the terminal viewport
        for y in range(Output_height):
            for x in range(Output_width):

                lx = min(Vid_width, x * Char_width)
                hx = min(Vid_width, (x + 1) * Char_width)
                ly = min(Vid_height, y * Char_height)
                hy = min(Vid_height, (y + 1) * Char_height)
                if (lx < hx and ly < hy):
                    output += Determine_Char(lx, hx, ly, hy, frame)
            if (y < Output_height - 1):
                output += "\n"
        with open(str(PROC_FRAME_DIR / f"{i}.txt"), "w") as textFrame:
            textFrame.write(output)

def DrawFrame():
    global Playback_index
    global refresh
    if (Playback_index < Vid_frames):
        with open(str(PROC_FRAME_DIR / f"{Playback_index}.txt"), "r") as ff:
            #print(ff.read())
            stdscr.clear()
            stdscr.addstr(ff.read(), curses.color_pair(1))
            refresh()

def PlaySound():
    playsound(str(AUDIO_DIR / 'sndfile.mp3'))

def clear():
    stdscr.clear()

def write():
    stdscr.addstr(str, curses.color_pair(1))

#main code block
def main():
    ExtractAudioTrack(sys.argv[1]) #run code for extracting audio information from file
    ExtractVideoFrames(sys.argv[1]) #run code to get all frames and move them to UNPROC_FRAME_DIR
    DetermineAspect() #get aspect ratio of terminal and video and determine fitting output size
    if (len(sys.argv) < 3):
        ASCIIFy() #turn all frames into .txt files ready to steam in
    
    global stdscr
    global refresh
    global Playback_index
    stdscr = curses.initscr()
    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    refresh = stdscr.refresh

    clear()
    curses.cbreak()
    curses.noecho()
    refresh()

    a = Thread(target=PlaySound)
    a.start()

    startTime = time.time()
    while Playback_index < Vid_frames:
        Playback_index = round((time.time() - startTime) * Vid_framerate)
        t = Thread(target=DrawFrame)
        t.start()
        time.sleep(1 / Vid_framerate)

    t.join()
    a.join()

    clear()
    refresh()
    curses.nocbreak()
    curses.echo()
    curses.endwin()


#basic input validation and let the rest of the file load first so all functions are already defined
if __name__ == "__main__":
    if (len(sys.argv) < 2):
        print("Usage: python VideoPlayer.py filename.ext")
        exit()
    else:
        main()