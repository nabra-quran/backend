from scipy.fftpack import dct

import numpy as np
import scipy.io.wavfile as wav

THRESHOLD = 0.05
ALPHA = 0.97
FRAME_SIZE = 0.025
FRAME_STRIDE = 0.01
SAMPLE_RATE = 16000
NUM_FILTERS = 26
MIN_FREQ = 0
N_FFT = 512
WINDOW_SIZE = 32768
NUM_CEPS = 13

def remove_silence(signal, threshold = THRESHOLD):
    signal[np.abs(signal) < threshold] = 0
    return signal

def pre_emphasis(signal, alpha = ALPHA):
    emphasized_signal = np.append(signal[0], signal[1:] - alpha * signal[:-1])
    return emphasized_signal

def framing(signal, frame_size = FRAME_SIZE, frame_stride = FRAME_STRIDE, sample_rate = SAMPLE_RATE):
    frame_length, frame_step = frame_size * sample_rate, frame_stride * sample_rate
    signal_length = len(signal)
    frame_length = int(round(frame_length))
    frame_step = int(round(frame_step))
    num_frames = int(np.ceil(float(np.abs(signal_length - frame_length)) / frame_step))
    padded_signal_length = num_frames * frame_step + frame_length
    z = np.zeros((padded_signal_length - signal_length))
    pad_signal = np.append(signal, z)
    indices = np.tile(np.arange(0, frame_length), (num_frames, 1)) + np.tile(np.arange(0, num_frames * frame_step, frame_step), (frame_length, 1)).T
    frames = pad_signal[indices.astype(np.int32, copy = False)]
    return frames

def apply_window(frames, window_func = np.hamming):
    frames *= window_func(frames.shape[1])
    return frames

def create_mel_filterbank(sample_rate, num_filters = NUM_FILTERS, min_freq = MIN_FREQ, max_freq = None, n_fft = N_FFT):
    if max_freq is None:
        max_freq = sample_rate // 2
    mel_min = 2595 * np.log10(1 + min_freq / 700)
    mel_max = 2595 * np.log10(1 + max_freq / 700)
    mel_points = np.linspace(mel_min, mel_max, num_filters + 2)
    hz_points = 700 * (10**(mel_points / 2595) - 1)
    bin_points = np.floor((n_fft + 1) * hz_points / sample_rate).astype(int)
    filterbank = np.zeros((num_filters, n_fft // 2 + 1))
    for i in range(1, num_filters + 1):
        filterbank[i - 1, bin_points[i - 1]:bin_points[i]] = (bin_points[i] - bin_points[i - 1]) / (hz_points[i] - hz_points[i - 1])
        filterbank[i - 1, bin_points[i]:bin_points[i + 1]] = (bin_points[i + 1] - bin_points[i]) / (hz_points[i + 1] - hz_points[i])
    return filterbank

def compute_mfcc(signal, sample_rate = SAMPLE_RATE, num_ceps = NUM_CEPS):
    frames = framing(signal, sample_rate = sample_rate)
    frames *= WINDOW_SIZE
    frames = apply_window(frames)
    magnitude_spectrum = np.abs(np.fft.rfft(frames, n = N_FFT))
    mel_filterbank = create_mel_filterbank(sample_rate, num_filters = NUM_FILTERS, n_fft = N_FFT)
    mel_spectrum = np.dot(magnitude_spectrum, mel_filterbank.T)
    log_mel_spectrum = np.log(mel_spectrum + 1e-10)
    mfcc = dct(log_mel_spectrum, type = 2, axis = 1, norm = 'ortho')[:, 1 : (num_ceps + 1)]
    return mfcc

def get_mfcc(wav_file):
    try:
        sample_rate, signal = wav.read(wav_file)
        signal = remove_silence(signal)
        signal = pre_emphasis(signal)
        mfcc = compute_mfcc(signal, sample_rate=sample_rate)
        return mfcc.tolist()
    except Exception as e:
        print(f"Error reading file {wav_file}: {e}")
        return None
