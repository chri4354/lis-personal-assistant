---
chapter: decision-trees
publish: true
source_files:
- (pasted input)
status: draft
title: Week 6 — Advanced Decision Tree Concepts and Hyperparameter Tuning
type: lecture-summary
---

# Week 6 — Advanced Decision Tree Concepts and Hyperparameter Tuning

## Overview

This session delves into the calculation of feature importance using impurity reduction, the interpretability of decision trees, and techniques for controlling overfitting through hyperparameter tuning and pruning. It also covers the sensitivity of decision trees to initial samples and methods like ensemble learning to improve stability.

## Key Concepts

- Feature importance based on impurity reduction (Gini impurity)
- Hyperparameter tuning and pruning to prevent overfitting
- Sensitivity of decision trees to initial data samples
- Ensemble methods such as decision forests to improve stability

## Examples & Case Studies

- Calculating feature importance by summing weighted impurity reductions across tree splits
- Visualizing decision trees and analyzing splits on features like income and petal width
- Demonstrating overfitting by increasing tree depth and observing test vs. training accuracy
- Using predict_proba to estimate class probabilities for new data points

## Questions Raised

- How is feature importance calculated in decision trees?
- Why can the Gini impurity exceed 0.5 when there are more than two classes?
- How does the choice of hyperparameters like max depth and min samples affect overfitting?
- What methods can be used to stabilize decision trees given their sensitivity to initial samples?

## Clarifications

- Gini impurity for two classes is capped at 0.5, but with more classes, it can be higher (up to 0.66 for three classes).
- Decision trees are sensitive to initial data samples, leading to different trees for different samples; ensemble methods like random forests help mitigate this instability.
- Overfitting occurs when increasing tree complexity improves training accuracy but reduces test accuracy; optimal hyperparameters balance this trade-off.
- Random seed settings ensure reproducibility of decision tree results across runs.

## Further Reading

- Scikit-learn documentation on Decision Trees and Random Forests
- Understanding Gini impurity and entropy in classification trees
- Techniques for pruning and hyperparameter tuning in decision trees
