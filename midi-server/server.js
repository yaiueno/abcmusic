require('dotenv').config();
const express = require('express');
const path = require('path');
const fs = require('fs');
const multer = require('multer');
const { parseMidi } = require('midi-file');
const { midiToNoteName } = require('@tonaljs/midi');
const { exec } = require('child_process');

const app = express();
const PORT = process.env.MIDI_PORT || 3001;

// LANアクセス対応のCORS設定
app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.header('Access-Control-Allow-Headers', 'Content-Type');
    if (req.method === 'OPTIONS') return res.sendStatus(200);
    next();
});

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// ------------------------------------------------------------------
// ファイルアップロード設定
// ------------------------------------------------------------------
const storage = multer.diskStorage({
    destination: (req, file, cb) => cb(null, __dirname),
    filename: (req, file, cb) => cb(null, 'uploaded_input.mid'),
});
const upload = multer({ storage });

// ------------------------------------------------------------------
// 音符変換定数
// ------------------------------------------------------------------
const SNAP_DURATIONS = [0.25, 0.5, 1, 1.5, 2, 3, 4];
const DURATION_SUFFIX = { 0.25: '/4', 0.5: '/2', 1: '', 1.5: '3/2', 2: '2', 3: '3', 4: '4' };

function snapDuration(d) {
    return SNAP_DURATIONS.reduce((best, v) => Math.abs(v - d) < Math.abs(best - d) ? v : best);
}

const BASE_NOTE_MAP = {
    'C': 'C', 'C#': '^C', 'D': 'D', 'D#': '^D', 'E': 'E', 'F': 'F',
    'F#': '^F', 'G': 'G', 'G#': '^G', 'A': 'A', 'A#': '^A', 'B': 'B',
};

// ------------------------------------------------------------------
// MIDI → ABC 変換エンジン (高精度版)
// ------------------------------------------------------------------
function convertMidiToAbcAdvanced(midiFilePath) {
    const midiBuffer = fs.readFileSync(midiFilePath);
    const midiData = parseMidi(midiBuffer);
    const abcHeader = 'X:1\nT:Converted MIDI\nM:4/4\nL:1/4\nK:C\n';
    let allNotes = [];
    const ticksPerBeat = midiData.header.ticksPerBeat || 480;

    midiData.tracks.forEach(track => {
        let absoluteTick = 0;
        const activeNotes = {};
        track.forEach(event => {
            absoluteTick += event.deltaTime;
            if (event.type === 'noteOn' && event.velocity > 0) {
                activeNotes[event.noteNumber] = absoluteTick;
            } else if (event.type === 'noteOff' || (event.type === 'noteOn' && event.velocity === 0)) {
                const startTick = activeNotes[event.noteNumber];
                if (startTick === undefined) return;
                const timeInBeats = startTick / ticksPerBeat;
                const durationInBeats = (absoluteTick - startTick) / ticksPerBeat;
                delete activeNotes[event.noteNumber];

                const noteName = midiToNoteName(event.noteNumber, { sharps: true });
                const match = noteName.match(/^([A-G]#?)(-?[0-9]+)$/);
                if (!match) return;
                const baseName = match[1];
                const octave = parseInt(match[2]);
                let abcNote = BASE_NOTE_MAP[baseName];
                if (!abcNote) return;
                if (octave === 5) abcNote = abcNote.toLowerCase();
                else if (octave > 5) abcNote = abcNote.toLowerCase() + "'".repeat(octave - 5);
                else if (octave < 4) abcNote = abcNote + ','.repeat(4 - octave);

                allNotes.push({ time: timeInBeats, duration: durationInBeats, note: abcNote });
            }
        });
    });

    allNotes.sort((a, b) => a.time - b.time);
    const quantization = 0.0625;
    const timeGroups = {};
    allNotes.forEach(n => {
        const qt = (Math.round(n.time / quantization) * quantization).toFixed(4);
        if (!timeGroups[qt]) timeGroups[qt] = [];
        timeGroups[qt].push(n);
    });

    let abcNotes = '';
    let currentBeat = 0;
    let measureBeat = 0;
    const BEATS_PER_MEASURE = 4;

    Object.keys(timeGroups).sort((a, b) => Number(a) - Number(b)).forEach(time => {
        const t = Number(time);
        const gap = t - currentBeat;
        if (gap > quantization / 2) {
            const snappedGap = snapDuration(gap);
            abcNotes += 'z' + (DURATION_SUFFIX[snappedGap] ?? '') + ' ';
            currentBeat += snappedGap;
            measureBeat += snappedGap;
            if (measureBeat >= BEATS_PER_MEASURE) { abcNotes += '|\n'; measureBeat -= BEATS_PER_MEASURE; }
        }
        const notesInGroup = timeGroups[time];
        const noteMap = new Map();
        notesInGroup.forEach(n => {
            if (!noteMap.has(n.note) || n.duration > noteMap.get(n.note).duration) noteMap.set(n.note, n);
        });
        const uniqueNotes = [...noteMap.values()];
        const snappedDur = snapDuration(Math.max(...uniqueNotes.map(n => n.duration)));
        if (uniqueNotes.length > 1) {
            const chordStr = uniqueNotes.map(n => n.note + (DURATION_SUFFIX[snapDuration(n.duration)] ?? '')).join('');
            abcNotes += '[' + chordStr + '] ';
        } else {
            abcNotes += uniqueNotes[0].note + (DURATION_SUFFIX[snappedDur] ?? '') + ' ';
        }
        currentBeat += snappedDur;
        measureBeat += snappedDur;
        if (measureBeat >= BEATS_PER_MEASURE) { abcNotes += '|\n'; measureBeat -= BEATS_PER_MEASURE; }
    });

    return abcHeader + (abcNotes || 'z4 |\n');
}

// ------------------------------------------------------------------
// ヘルスチェック
// ------------------------------------------------------------------
app.get('/api/health', (req, res) => {
    res.json({ status: 'ok', service: 'midi-server', port: PORT });
});

// ------------------------------------------------------------------
// POST /api/upload-convert  MIDI → ABC
// ------------------------------------------------------------------
app.post('/api/upload-convert', upload.single('midiFile'), (req, res) => {
    if (!req.file) {
        return res.status(400).json({ status: 'error', message: 'ファイルが受信できませんでした。' });
    }
    try {
        const abcResult = convertMidiToAbcAdvanced(path.join(__dirname, 'uploaded_input.mid'));
        fs.mkdirSync(path.join(__dirname, 'public'), { recursive: true });
        fs.writeFileSync(path.join(__dirname, 'public', 'result.abc'), abcResult, 'utf-8');
        res.json({ status: 'success', message: 'MIDIからABCへの高精度変換に成功しました！', abc_text: abcResult });
    } catch (error) {
        console.error(error);
        res.status(500).json({ status: 'error', message: '変換に失敗しました。' });
    }
});

// ------------------------------------------------------------------
// POST /api/text-to-midi  ABC → MIDI (abc2midi)
// ------------------------------------------------------------------
app.post('/api/text-to-midi', (req, res) => {
    const { abcText } = req.body;
    if (!abcText) return res.status(400).json({ status: 'error', message: 'テキストが空です。' });

    const tempAbcPath = path.join(__dirname, 'temp_input.abc');
    // 共有output/ディレクトリにMIDIを保存（FastAPIの/output/経由で配信）
    const OUTPUT_DIR = process.env.OUTPUT_DIR || path.join(__dirname, '..', 'output');
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
    const outputMidiPath = path.join(OUTPUT_DIR, 'generated_output.mid');

    try {
        fs.writeFileSync(tempAbcPath, abcText, 'utf-8');
        const isWin = process.platform === 'win32';
        const abc2midiExe = path.join(__dirname, isWin ? 'abc2midi.exe' : 'abc2midi');
        const command = `"${abc2midiExe}" "${tempAbcPath}" -o "${outputMidiPath}"`;

        exec(command, (error, stdout, stderr) => {
            if (fs.existsSync(tempAbcPath)) fs.unlinkSync(tempAbcPath);
            if (error) {
                console.error(`abc2midi エラー: ${error.message}`);
                return res.status(500).json({ status: 'error', message: 'abc2midiの実行に失敗しました。' });
            }
            res.json({
                status: 'success',
                message: 'abc2midiによるMIDI変換に成功！',
                // FastAPIの/output/経由でダウンロードする
                midi_url: '/output/generated_output.mid',
            });
        });
    } catch (error) {
        console.error(error);
        res.status(500).json({ status: 'error', message: 'システムエラーが発生しました。' });
    }
});

// ------------------------------------------------------------------
// 変換済みABCテキスト取得 (Pythonプロキシ用)
// ------------------------------------------------------------------
app.get('/result.abc', (req, res) => {
    const resultPath = path.join(__dirname, 'public', 'result.abc');
    if (fs.existsSync(resultPath)) {
        res.type('text/plain').sendFile(resultPath);
    } else {
        res.status(404).json({ status: 'error', message: 'result.abc が見つかりません。' });
    }
});

app.listen(PORT, () => {
    console.log('='.repeat(45));
    console.log('  ABC Music Suite - MIDI Server');
    console.log(`  ポート: ${PORT}`);
    console.log(`  MIDI→ABC変換: POST /api/upload-convert`);
    console.log(`  ABC→MIDI変換: POST /api/text-to-midi`);
    console.log('='.repeat(45));
});
