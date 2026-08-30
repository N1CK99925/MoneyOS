import { SylvaHero } from "@designcodeio/threeui";
import "@designcodeio/threeui/style.css";

export default function Landing() {
  return (
    <div className="shader-frame">
      <SylvaHero
        headingFont="newsreader"
        bodyFont="geist"
        headingWeight="300"
        bodyWeight="300"
        primaryColor="#ffffff"
        headingSize={63}
        bodySize={16.5}
        headingLetterSpacing={-0.006}
      />
    </div>
  );
}
