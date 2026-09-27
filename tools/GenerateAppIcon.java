import java.awt.BasicStroke;
import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.awt.image.BufferedImage;
import java.awt.geom.RoundRectangle2D;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import javax.imageio.ImageIO;

final class GenerateAppIcon {
    private GenerateAppIcon() {}

    public static void main(String[] args) throws IOException {
        if (args.length < 2 || args.length > 3) {
            throw new IllegalArgumentException(
                "Usage: java tools/GenerateAppIcon.java OUTPUT.png SIZE [--android]"
            );
        }

        Path output = Path.of(args[0]);
        int size = Integer.parseInt(args[1]);
        if (size < 16) {
            throw new IllegalArgumentException("SIZE must be at least 16 pixels");
        }

        boolean androidLegacy = args.length == 3 && "--android".equals(args[2]);
        if (args.length == 3 && !androidLegacy) {
            throw new IllegalArgumentException("The only supported mode is --android");
        }

        BufferedImage image = new BufferedImage(
            size,
            size,
            androidLegacy ? BufferedImage.TYPE_INT_ARGB : BufferedImage.TYPE_INT_RGB
        );
        Graphics2D graphics = image.createGraphics();
        try {
            graphics.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            graphics.setRenderingHint(RenderingHints.KEY_RENDERING, RenderingHints.VALUE_RENDER_QUALITY);
            graphics.setColor(new Color(0x17, 0x6B, 0x5B));
            if (androidLegacy) {
                float inset = size * 0.04f;
                float diameter = size - inset * 2;
                graphics.fill(new RoundRectangle2D.Float(
                    inset,
                    inset,
                    diameter,
                    diameter,
                    size * 0.22f,
                    size * 0.22f
                ));
            } else {
                graphics.fillRect(0, 0, size, size);
            }

            float stroke = size * 0.095f;
            float left = size * 0.30f;
            float top = size * 0.24f;
            float middle = size * 0.50f;
            float bottom = size * 0.76f;
            float armEnd = size * 0.68f;

            graphics.setColor(Color.WHITE);
            graphics.setStroke(new BasicStroke(stroke, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND));
            graphics.drawLine(Math.round(left), Math.round(top), Math.round(left), Math.round(bottom));
            graphics.drawLine(Math.round(left), Math.round(top), Math.round(armEnd), Math.round(top));
            graphics.drawLine(Math.round(left), Math.round(middle), Math.round(armEnd), Math.round(middle));
            graphics.drawLine(Math.round(left), Math.round(bottom), Math.round(armEnd), Math.round(bottom));

            graphics.setColor(new Color(0xBD, 0xE8, 0xDE));
            graphics.setStroke(new BasicStroke(size * 0.034f, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND));
            float nodeX = size * 0.79f;
            float nodeRadius = size * 0.038f;
            for (float y : new float[] {top, middle, bottom}) {
                graphics.drawLine(Math.round(armEnd), Math.round(y), Math.round(nodeX), Math.round(y));
                graphics.fillOval(
                    Math.round(nodeX - nodeRadius),
                    Math.round(y - nodeRadius),
                    Math.round(nodeRadius * 2),
                    Math.round(nodeRadius * 2)
                );
            }
        } finally {
            graphics.dispose();
        }

        Files.createDirectories(output.toAbsolutePath().getParent());
        if (!ImageIO.write(image, "png", output.toFile())) {
            throw new IOException("No PNG writer is available");
        }
    }
}
