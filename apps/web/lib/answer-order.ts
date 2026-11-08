import type { PublicItem } from "./contracts";

// Presentation only: canonical option indices stay private to the data client.
export function shuffleAnswers(item: PublicItem, random = Math.random) {
  const order = item.options.map((_, index) => index);
  for (let index = order.length - 1; index > 0; index--) {
    const other = Math.floor(random() * (index + 1));
    [order[index], order[other]] = [order[other], order[index]];
  }
  return {
    item: { ...item, options: order.map((index) => item.options[index]) },
    order,
  };
}
