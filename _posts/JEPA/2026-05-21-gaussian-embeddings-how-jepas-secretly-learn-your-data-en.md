---
layout: post
title: "Gaussian Embeddings: How JEPAs Secretly Learn Your Data"
date: 2026-05-21
lang: en
slug_id: gaussian-embeddings-how-jepas-secretly-learn-your-data
permalink: /blog-en/gaussian-embeddings-how-jepas-secretly-learn-your-data/
---

### TL;DR

JEPAs are essentially trained with a combination of two objective functions.

1. Prediction term: predicting the original representation from a perturbed representation, predicting the next state in dynamics, etc.
2. Anti-collapse term: preventing all observations from being mapped to the same representation.

While (2) has so far been regarded as merely a regularization term, the claim is that this term implicitly **forces the model to estimate the data distribution $p_X$** (even though JEPAs do not perform generation).

- A method for extracting $p_X$ is proposed as JEPA-SCORE.

### Outline of the Theory

#### Lemma 1. A high-dimensional Gaussian distribution becomes a uniform distribution on a hypersphere

A $K$-dimensional standard Gaussian distribution, when normalized by $\sqrt{K}$, **converges to a uniform distribution on the unit hypersphere as $K$ grows large**. (High-dimensional statistics)

- In other words, "making embeddings Gaussian" ≒ "making them uniform on a hypersphere."

#### Lemma 2. To generate Gaussian embeddings, the model must learn the data density

- This is the case when representations are regularized to be Gaussian.

The output density of a neural network $f$ can be expressed using the singular values of the Jacobian matrix via the change-of-variables formula:

$p_{f(X)}(f(x)) = \int \frac{p_X(x)}{\prod_k \sigma_k (J_f(u))} d\mathcal{H}^r(u)$

For the left-hand side to be uniform (i.e., constant), the product of the singular values of the Jacobian matrix must be proportional to $p_X$. That is, **in order to embed into a Gaussian distribution, $f$ must internally learn the data density**.

### By the way

#### Regarding Lemma 1

Any isotropic distribution with iid components, when normalized in high dimensions, approaches a uniform distribution on a hypersphere (concentration of measure phenomenon). So what makes the Gaussian distribution special?

- Under the covariance constraint

#### Regarding Lemma 2

-
