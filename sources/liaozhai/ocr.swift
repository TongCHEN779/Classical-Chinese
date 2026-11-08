// macOS local OCR cache. Usage: ocr SOURCE.pdf START END CACHE_DIR
// Drafts only: inspect page images before publishing any text into src/.
import Foundation
import Vision
import PDFKit
import AppKit
struct Line: Codable {
    let text: String
    let confidence: Float
    let x: Double, y: Double, width: Double, height: Double
}
struct PageResult: Codable { let page: Int; let lines: [Line] }
let args = CommandLine.arguments
guard args.count == 5, let first = Int(args[2]), let last = Int(args[3]),
      let document = PDFDocument(url: URL(fileURLWithPath: args[1])),
      first >= 1, last >= first, last <= document.pageCount else {
    fputs("Usage: ocr SOURCE.pdf START END CACHE_DIR\n", stderr); exit(2)
}
let output = URL(fileURLWithPath: args[4], isDirectory: true)
try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
let encoder = JSONEncoder()
encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
var failures = 0
for number in first...last {
    let dest = output.appendingPathComponent(String(format: "%04d.json", number))
    if FileManager.default.fileExists(atPath: dest.path) { continue }
    autoreleasepool {
        let image = document.page(at: number - 1)!.thumbnail(of: NSSize(width: 1600, height: 2400), for: .mediaBox)
        var rectangle = NSRect(origin: .zero, size: image.size)
        guard let cg = image.cgImage(forProposedRect: &rectangle, context: nil, hints: nil) else {
            failures += 1; fputs("Cannot render page \(number)\n", stderr); return
        }
        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.recognitionLanguages = ["zh-Hans", "zh-Hant"]
        request.usesLanguageCorrection = false
        do {
            try VNImageRequestHandler(cgImage: cg).perform([request])
            let lines = (request.results ?? []).compactMap { observation -> Line? in
                guard let candidate = observation.topCandidates(1).first else { return nil }
                let b = observation.boundingBox
                return Line(text: candidate.string, confidence: candidate.confidence,
                            x: Double(b.minX), y: Double(b.minY), width: Double(b.width), height: Double(b.height))
            }
            guard !lines.isEmpty else { throw NSError(domain: "EmptyOCR", code: number) }
            try encoder.encode(PageResult(page: number, lines: lines)).write(to: dest, options: .atomic)
            if number % 25 == 0 || number == first || number == last { print("OCR page \(number)/\(last)"); fflush(stdout) }
        } catch {
            failures += 1; fputs("Page \(number): \(error)\n", stderr)
        }
    }
}
if failures > 0 { fputs("\(failures) page(s) failed; rerun to retry missing pages.\n", stderr); exit(1) }
