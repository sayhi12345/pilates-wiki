import AppKit
import Foundation
import Vision

struct OCRLine: Codable {
    let text: String
    let x: Double
    let y: Double
    let width: Double
    let height: Double
    let boxes: [OCRCharBox]
}

struct OCRCharBox: Codable {
    let text: String
    let x: Double
    let y: Double
    let width: Double
    let height: Double
}

struct OCRBoxPage: Codable {
    let page: Int
    let image: String
    let width: Int
    let height: Int
    let lines: [OCRLine]
}

func pageNumber(from path: String) -> Int {
    let name = URL(fileURLWithPath: path).deletingPathExtension().lastPathComponent
    let digits = name.split(separator: "-").last ?? ""
    return Int(digits) ?? 0
}

func recognize(path: String) throws -> OCRBoxPage {
    let url = URL(fileURLWithPath: path)
    guard
        let image = NSImage(contentsOf: url),
        let tiff = image.tiffRepresentation,
        let bitmap = NSBitmapImageRep(data: tiff),
        let cgImage = bitmap.cgImage
    else {
        throw NSError(domain: "vision_ocr_boxes", code: 1, userInfo: [NSLocalizedDescriptionKey: "Cannot load image: \(path)"])
    }

    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true
    request.recognitionLanguages = ["zh-Hans", "en-US"]

    let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
    try handler.perform([request])

    let lines = (request.results ?? [])
        .compactMap { observation -> OCRLine? in
            guard let candidate = observation.topCandidates(1).first else { return nil }
            let string = candidate.string
            let box = observation.boundingBox
            var boxes: [OCRCharBox] = []
            var index = string.startIndex
            while index < string.endIndex {
                let next = string.index(after: index)
                let text = String(string[index..<next])
                defer { index = next }
                if text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                    continue
                }
                guard let charBox = try? candidate.boundingBox(for: index..<next) else {
                    continue
                }
                let charRect = charBox.boundingBox
                boxes.append(
                    OCRCharBox(
                        text: text,
                        x: Double(charRect.minX),
                        y: Double(charRect.minY),
                        width: Double(charRect.width),
                        height: Double(charRect.height)
                    )
                )
            }
            return OCRLine(
                text: string,
                x: Double(box.minX),
                y: Double(box.minY),
                width: Double(box.width),
                height: Double(box.height),
                boxes: boxes
            )
        }
        .sorted { left, right in
            let leftTop = left.y + left.height
            let rightTop = right.y + right.height
            if abs(leftTop - rightTop) > 0.012 {
                return leftTop > rightTop
            }
            return left.x < right.x
        }

    return OCRBoxPage(
        page: pageNumber(from: path),
        image: path,
        width: bitmap.pixelsWide,
        height: bitmap.pixelsHigh,
        lines: lines
    )
}

let encoder = JSONEncoder()
encoder.outputFormatting = [.sortedKeys]

for path in CommandLine.arguments.dropFirst() {
    do {
        let page = try recognize(path: path)
        let data = try encoder.encode(page)
        if let line = String(data: data, encoding: .utf8) {
            print(line)
            fflush(stdout)
        }
    } catch {
        fputs("OCR failed for \(path): \(error)\n", stderr)
    }
}
