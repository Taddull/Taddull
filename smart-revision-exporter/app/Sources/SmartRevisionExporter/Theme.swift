import SwiftUI

/// Visual language: dark, quiet surfaces, one accent, clear state colours.
enum Theme {
    static let background = Color(red: 0.067, green: 0.071, blue: 0.082)
    static let surface = Color(red: 0.102, green: 0.106, blue: 0.122)
    static let surfaceRaised = Color(red: 0.133, green: 0.137, blue: 0.157)
    static let hairline = Color.white.opacity(0.08)
    static let textPrimary = Color.white.opacity(0.92)
    static let textSecondary = Color.white.opacity(0.58)
    static let textTertiary = Color.white.opacity(0.38)

    static let accent = Color(red: 0.36, green: 0.62, blue: 1.0)          // revised frames
    static let boundary = Color(red: 0.98, green: 0.71, blue: 0.29)       // codec expansion
    static let preserved = Color.white.opacity(0.10)                       // untouched frames
    static let success = Color(red: 0.30, green: 0.80, blue: 0.53)
    static let warning = Color(red: 0.98, green: 0.71, blue: 0.29)
    static let failure = Color(red: 0.96, green: 0.38, blue: 0.38)

    static let corner: CGFloat = 10
    static let mono = Font.system(.body, design: .monospaced)
    static let monoSmall = Font.system(size: 11, weight: .regular, design: .monospaced)
    static let title = Font.system(size: 13, weight: .semibold)
    static let caption = Font.system(size: 11, weight: .medium)
}

struct Card<Content: View>: View {
    let title: String
    var trailing: AnyView? = nil
    @ViewBuilder var content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text(title.uppercased())
                    .font(Theme.caption)
                    .tracking(0.8)
                    .foregroundStyle(Theme.textTertiary)
                Spacer()
                if let t = trailing { t }
            }
            content
        }
        .padding(16)
        .background(RoundedRectangle(cornerRadius: Theme.corner).fill(Theme.surface))
        .overlay(RoundedRectangle(cornerRadius: Theme.corner).stroke(Theme.hairline, lineWidth: 1))
    }
}

struct KeyValueRow: View {
    let key: String
    let value: String
    var mono: Bool = false

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 12) {
            Text(key)
                .font(.system(size: 12))
                .foregroundStyle(Theme.textSecondary)
                .frame(width: 92, alignment: .leading)
            Text(value)
                .font(mono ? Theme.monoSmall : .system(size: 12, weight: .medium))
                .foregroundStyle(Theme.textPrimary)
                .lineLimit(2)
                .truncationMode(.middle)
                .textSelection(.enabled)
            Spacer(minLength: 0)
        }
    }
}

struct StatusDot: View {
    let color: Color
    var body: some View {
        Circle().fill(color).frame(width: 8, height: 8)
            .shadow(color: color.opacity(0.6), radius: 3)
    }
}

struct Pill: View {
    let text: String
    let color: Color
    var body: some View {
        Text(text)
            .font(.system(size: 10, weight: .semibold))
            .padding(.horizontal, 7)
            .padding(.vertical, 3)
            .background(Capsule().fill(color.opacity(0.16)))
            .foregroundStyle(color)
    }
}

struct PrimaryButtonStyle: ButtonStyle {
    var enabled: Bool = true
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 13, weight: .semibold))
            .padding(.horizontal, 18)
            .padding(.vertical, 9)
            .background(RoundedRectangle(cornerRadius: 8)
                .fill(enabled ? Theme.accent.opacity(configuration.isPressed ? 0.75 : 1) : Theme.surfaceRaised))
            .foregroundStyle(enabled ? Color.white : Theme.textTertiary)
            .animation(.easeOut(duration: 0.12), value: configuration.isPressed)
    }
}

struct QuietButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 12, weight: .medium))
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(RoundedRectangle(cornerRadius: 7)
                .fill(Theme.surfaceRaised.opacity(configuration.isPressed ? 0.6 : 1)))
            .overlay(RoundedRectangle(cornerRadius: 7).stroke(Theme.hairline))
            .foregroundStyle(Theme.textPrimary)
    }
}
